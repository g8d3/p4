#!/usr/bin/env python3
"""One Edge Terminal agent cycle: probe the server, summarize state, render desk.html.

Idempotent and read-only with respect to money (it never touches positions).
Cycle = one probe + one row in data/loop_log.jsonl + one desk.html render.
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = json.loads((ROOT / "server" / "config.json").read_text())["server"]["port"]
BASE = f"http://127.0.0.1:{PORT}"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)


def get(path, timeout=25):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read().decode())


def now():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def main():
    try:
        status = get("/api/status")
    except Exception as e:  # server down is itself a reportable state
        print(f"DOWN: {e}", file=sys.stderr)
        render({"error": str(e)})
        return 2

    def safe(path):
        try:
            return get(path, timeout=90)
        except Exception as e:
            return {"error": str(e)}

    track = safe("/api/track")
    backtest = safe("/api/backtest")
    ledger = safe("/api/ledger?limit=40")

    row = {
        "ts": int(time.time() * 1000),
        "when": now(),
        "uptime_sec": status.get("uptimeSec"),
        "requests": status.get("stats", {}).get("requests"),
        "upstream_err": status.get("stats", {}).get("upstreamErr"),
        "cache_entries": len(status.get("cache", [])),
        "signals": status.get("counts", {}).get("signals"),
        "ledger_rows": status.get("counts", {}).get("ledger"),
        "killed": status.get("killed"),
        "human_go": status.get("humanGo"),
        "track_win": (track.get("summary") or {}).get("winRate"),
        "track_resolved": (track.get("summary") or {}).get("resolved"),
        "bt_win": (backtest.get("summary") or {}).get("winRate"),
        "bt_total": (backtest.get("summary") or {}).get("total"),
    }
    with (DATA / "loop_log.jsonl").open("a") as f:
        f.write(json.dumps(row) + "\n")

    render({"status": status, "track": track, "backtest": backtest, "ledger": ledger, "row": row})
    print(
        f"cycle ok — requests={row['requests']} signals={row['signals']} "
        f"ledger={row['ledger_rows']} killed={row['killed']} human_go={row['human_go']}"
    )
    return 0


def esc(v):
    return (str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if v is not None else "—")


def kv(rows):
    return "".join(f'<div class="k">{esc(k)}</div><div class="v {c}">{esc(v)}</div>'
                   for k, v, c in rows)


def render(ctx):
    st = ctx.get("status") or {}
    err = ctx.get("error")
    tr = ctx.get("track") or {}
    bt = ctx.get("backtest") or {}
    led = ctx.get("ledger") or {}
    row = ctx.get("row") or {}
    stats = st.get("stats", {}) or {}
    ts = (tr.get("summary") or {})
    bs = (bt.get("summary") or {})
    rows = (led.get("rows") or [])[-12:]
    needs = (st.get("needs") or {})

    gates = kv([
        ("Mode", st.get("mode", "unknown"), ""),
        ("Kill switch", "ENGAGED" if st.get("killed") else "clear", "down" if st.get("killed") else "up"),
        ("HUMAN_GO (live money)", "granted" if st.get("humanGo") else "not granted", "up" if st.get("humanGo") else "down"),
        ("Signals logged", row.get("signals", "—"), ""),
        ("Ledger rows", row.get("ledger_rows", "—"), ""),
    ])

    pulse = kv([
        ("When", row.get("when", "n/a"), ""),
        ("Uptime", f"{row.get('uptime_sec', 0)}s", ""),
        ("Requests", row.get("requests", "—"), ""),
        ("Upstream errors", row.get("upstream_err", "—"), "down" if row.get("upstream_err") else "up"),
        ("Cache entries", row.get("cache_entries", "—"), ""),
        ("Last cycle", f"{len(str(err) or '') or 'ok'}", "down" if err else "up"),
    ])

    receipt = kv([
        (f"Backtest ({(bt.get('cfg') or {}).get('days', '?')}d)",
         f"{bs.get('winRate', '—')}% hit · {bs.get('avgR', '—')}R avg · {bs.get('total', '—')} calls", ""),
        ("Live calls resolved", f"{ts.get('resolved', 0)} · {ts.get('winRate', '—')}% win", ""),
        ("Live calls pending", ts.get("pending", "—"), ""),
        ("Errors", esc(err) if err else "none", "down" if err else "up"),
    ])

    ledger_html = "".join(
        f"<tr><td>{esc(datetime.fromtimestamp(r['ts']/1000).strftime('%b %d, %H:%M'))}</td>"
        f"<td>{esc(r.get('event'))}</td><td>{esc(r.get('coin') or r.get('symbol'))}</td>"
        f"<td>{esc(r.get('side'))}</td><td class='num'>{esc(r.get('entry'))}</td>"
        f"<td class='num'>{esc(r.get('exit'))}</td>"
        f"<td class='num {'up' if (r.get('pnl') or 0) > 0 else 'down' if (r.get('pnl') or 0) < 0 else ''}'>"
        f"{esc(r.get('pnl'))}</td><td>{esc(r.get('reason') or '')}</td></tr>"
        for r in rows) or "<tr><td colspan='8' class='empty'>no rows yet</td></tr>"

    secret_rows = "".join(
        f"<tr><td>{esc(s.get('id'))}</td><td>{esc(s.get('what'))} — {esc(s.get('why'))}</td>"
        f"<td>{esc(s.get('status'))}</td></tr>"
        for s in (needs.get("secrets") or []))

    html = f"""<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Edge Terminal — desk</title><link rel=stylesheet href="/style.css">
<style>.desk{{max-width:1100px;margin:0 auto;padding:16px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}}
h2{{font-size:15px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:22px 0 8px}}
.panel{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:13px}}</style>
<body style="background:var(--bg)">
<header class="topbar"><div class="brand"><span class="logo">▲</span> EDGE <em>desk</em></div>
<div class="ticker"><span class="tk">observer view — one row per agent cycle</span></div>
<div class="topbar-right"><a class="btn ghost sm" href="/">app</a>
<a class="btn ghost sm" href="/admin.html">admin</a></div></header>
<main class="desk">
{('<div class="killbanner">Server unreachable: ' + esc(err) + '</div>') if err else ''}
<div class="cards">
  <div class="panel"><h2>Pulse</h2><div class="kv">{pulse}</div></div>
  <div class="panel"><h2>Gates</h2><div class="kv">{gates}</div></div>
  <div class="panel"><h2>Receipts</h2><div class="kv">{receipt}</div></div>
</div>
<h2>Closed paper trades (server ledger)</h2>
<div class="tablewrap"><table class="grid"><thead><tr><th>When</th><th>Event</th><th>Market</th>
<th>Side</th><th class=num>Entry</th><th class=num>Exit</th><th class=num>PnL</th><th>Reason</th>
</tr></thead><tbody>{ledger_html}</tbody></table></div>
<h2>What the human must provide (needs.json)</h2>
<div class="tablewrap"><table class="grid"><thead><tr><th>Item</th><th>Why</th><th>Status</th>
</tr></thead><tbody>{secret_rows or "<tr><td colspan=3 class='empty'>nothing pending</td></tr>"}</tbody></table></div>
<p class="footnote">Rendered {now()} · loop writes data/loop_log.jsonl · kill with data/LOOP_STOP · served at /desk.html</p>
</main></body>"""
    (ROOT / "public" / "desk.html").write_text(html)


if __name__ == "__main__":
    sys.exit(main())
