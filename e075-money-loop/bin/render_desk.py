#!/usr/bin/env python3
"""Rebuild desk.html. Plain language first, builder details last. Stdlib only."""
import json
import pathlib
import html
import time
import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(p, default=None):
    try:
        return json.loads((ROOT / p).read_text())
    except Exception:
        return default


def esc(s):
    return html.escape(str(s))


def ago(ts):
    try:
        t = datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
        s = int(time.time() - t)
    except Exception:
        return "unknown time"
    if s < 60:
        return f"{s} seconds ago"
    if s < 3600:
        return f"{s // 60} minutes ago"
    if s < 86400:
        return f"{s // 3600} hours ago"
    return f"{s // 86400} days ago"


cfg = load("data/config.json", {}) or {}
bt = load("log/backtest.json", {}) or {}
bal = load("log/balance.json", {}) or {}
beat = load("data/heartbeat.json", {}) or {}
stopped = (ROOT / "STOP").exists()
human_ok = (ROOT / "data" / "human_go.txt").read_text().strip() == "GO" if (ROOT / "data" / "human_go.txt").exists() else False

rows = []
p = ROOT / "data" / "ledger.jsonl"
if p.exists():
    for line in p.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
n_iters = len(rows)

daemon_alive = False
try:
    import os as _os
    _os.kill(int((ROOT / "log" / "cycle.lock").read_text().strip()), 0)
    daemon_alive = True
except Exception:
    pass

overall = bt.get("overall", "not computed yet")
strategies = bt.get("strategies", {}) or {}
rev = (strategies.get("S_REV", {}) or {}).get("oos", {}) or {}
fund = (strategies.get("S_FUND", {}) or {}).get("oos", {}) or {}

# ---- plain-language status ----
if stopped:
    headline = "Paused. The machine is stopped and your money is untouched."
    color, border = "#f8d7da", "#dc3545"
elif not rows:
    headline = "Starting up. No checks have run yet."
    color, border = "#fff3cd", "#e6c200"
elif daemon_alive:
    headline = ("Awake and checking on its own. "
                f"Last check {ago(beat.get('ts'))}, next one in about 30 minutes. "
                "Your money is untouched.")
    color, border = "#d4edda", "#28a745"
else:
    headline = (f"Last check {ago(beat.get('ts'))}, but the automatic schedule is off. "
                "Checks are running by hand until it is switched back on. "
                "Your money is untouched.")
    color, border = "#fff3cd", "#e6c200"

# ---- wallet in plain words ----
perp = bal.get("perp") or {}
spot = bal.get("spot") or {}
evm = bal.get("evm_arbitrum_usdc") or {}
addr = bal.get("address_prefix", "unknown")
perp_v = perp.get("accountValue")
spot_v = spot.get("accountValue")
if perp_v is None and spot_v is None and not evm.get("ok"):
    wallet_line = (f"Wallet {esc(addr)}: could not be read right now "
                   "(the network blocked the balance check). Nothing was moved.")
else:
    parts = []
    parts.append(f"trading account: {esc(perp_v) if perp_v is not None else 'no data'}")
    parts.append(f"spot account: {esc(spot_v) if spot_v is not None else 'no data'}")
    if evm.get("ok"):
        parts.append(f"Arbitrum dollars: {evm.get('usdc')}")
    else:
        parts.append("Arbitrum dollars: could not be read right now")
    wallet_line = f"Wallet {esc(addr)} — " + ", ".join(parts) + ". Nothing was moved."

# ---- strategies in plain words ----
def plain_strat(title, oos, what_it_does):
    n = oos.get("n", 0) or 0
    exp = oos.get("expectancy")
    try:
        pct = f"{float(exp) * 100:+.2f}% per trade"
    except (TypeError, ValueError):
        pct = "no result yet"
    wins = oos.get("win_rate")
    try:
        winline = f", won {float(wins) * 100:.0f}% of them"
    except (TypeError, ValueError):
        winline = ""
    return (f"<h3>{esc(title)}</h3><p>{esc(what_it_does)} "
            f"In the second half of the price history it would have traded "
            f"<b>{n} times</b>, averaging <b>{pct}</b>{winline} after fees.</p>")


rev_txt = plain_strat(
    "Strategy 1: buy the dip after bad days",
    rev,
    "After a very bad day, or a down day almost nobody traded, it buys and holds for 5 days.")
fund_txt = plain_strat(
    "Strategy 2: bet against the crowd",
    fund,
    "When most traders pile in one direction, it bets the other way for 1 day.")

if overall == "GO":
    verdict_line = ("Verdict: strategy 1 looks good on paper and is the current candidate. "
                    "No real money moves until you approve it in writing.")
elif overall == "NOGO":
    verdict_line = ("Verdict: neither strategy looks good enough. "
                    "No real money moves. The machine keeps watching.")
else:
    verdict_line = "Verdict: still computing."

# ---- honest history (who ran what) ----
hist = ""
for r in reversed(rows[-10:]):
    actor = r.get("actor", "unknown")
    who = "automatic check" if actor == "daemon" else ("my builder's manual run" if actor == "builder" else esc(actor))
    hist += (f"<tr><td>{esc(r.get('ts', ''))}</td>"
             f"<td>{who}</td><td>{esc(r.get('result', ''))}</td></tr>\n")
if not hist:
    hist = "<tr><td colspan=3>Nothing has run yet.</td></tr>"

now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
caps = cfg.get("caps", {}) or {}

desk = f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Money Loop — is my money working?</title>
<style>body{{font-family:system-ui,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;line-height:1.55}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:.35rem .5rem;font-size:.9rem;text-align:left}}th{{background:#f5f5f5}}small,.dim{{color:#666}}#pulse{{padding:.9rem 1.1rem;border-radius:10px;font-size:1.05rem;background:{color};border:2px solid {border}}}details{{margin-top:1rem;border:1px solid #ccc;border-radius:8px;padding:.6rem 1rem}}summary{{cursor:pointer;font-weight:600}}</style>
<meta http-equiv=refresh content=60></head><body>
<h1>Is my money working?</h1>
<div id=pulse>{esc(headline)}</div>
<p><small>Updated {now} · this page refreshes every minute · you never need to read the chat.</small></p>

<h2>Your money</h2>
<p><b>$0 spent. 0 orders placed.</b> This version of the program cannot place orders — that part has not been built. Spending limits for the future: max ${caps.get('max_action_usd', '?')} per trade, ${caps.get('max_total_usd', '?')} total, full stop if losses pass ${caps.get('stop_loss_usd', '?')}.</p>
<p>{wallet_line}</p>

<h2>The two strategies</h2>
{rev_txt}
{fund_txt}
<p><b>{esc(verdict_line)}</b>{' Your written approval is still missing.' if not human_ok else ''}</p>

<h2>What this program is (and isn't)</h2>
<p>It is a fixed checklist, not a thinking mind: re-check the two strategies on old price data, peek at the wallet without touching it, write down the result, redraw this page. No artificial intelligence runs inside it. The AI is the builder outside it — the one who wrote this page and improves the checklist between runs.</p>

<h2>Latest checks (who ran them)</h2>
<table><tr><th>when</th><th>who ran it</th><th>result</th></tr>{hist}</table>

<details><summary>Details for the builder (numbers, gates, controls)</summary>
<p class=dim>Overall: {esc(overall)} · checks run: {n_iters} · written approval: {'yes' if human_ok else 'no'} · "
S_REV out-of-sample: {esc(rev)} · S_FUND out-of-sample: {esc(fund)}</p>
<p class=dim>Stop it any time by creating a file called STOP in the program folder; delete it to resume. The automatic schedule runs every 30 minutes. Contracts: AGENTS.md · data/config.json · data/ledger.jsonl</p>
</details>
</body></html>"""
(ROOT / "desk.html").write_text(desk)
print(f"desk rendered ({n_iters} iters, backtest={overall})")
