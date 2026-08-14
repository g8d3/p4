#!/usr/bin/env python3
"""Paper-trade monitor for the e025 Daily Decline Reversion strategy.

Runs daily via cron (00:15 UTC). For each coin:
  1. Fetch 1d candles (trailing ~420 days) from Hyperliquid candleSnapshot.
  2. Compute causal statistics: sigma (trailing 365d stdev of returns),
     volume ratio v/median_v (101-causal trailing median), q20 threshold.
  3. Evaluate the latest CLOSED daily candle for the two triggers:
       T1 crash          : ret < -3 * sigma
       T2 low-volume down: ret < 0 and v/median_v < q20
  4. On trigger: open a paper trade (entry close, exit 5 days later) and
     push a phone notification via e000-fundamentals/bin/notify.sh.
  5. On exit day: close the trade, log P&L net of taker fees, notify.

Idempotent: each day's latest closed candle is processed once (state in
output/paper_state.json). Run as:  zsh -c 'cd ... && python3 bin/paper_trade.py'
(zsh reads ~/.zshenv so NTFY_TOPIC is available).
"""
import csv, json, os, statistics, sys, time, urllib.request

URL = "https://api.hyperliquid.xyz/info"
DAY_MS = 86400000
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(os.path.dirname(HERE), "output")
NOTIFY = os.path.join(ROOT, "..", "e000-fundamentals", "bin", "notify.sh")

COINS = ["BTC", "ETH", "HYPE", "SOL", "PUMP", "ZEC", "XRP", "LIT", "DOGE", "CRV", "AAVE", "XMR"]
FETCH_DAYS = 420
SIGMA_WIN = 365
VOL_WIN = 101
Q = 0.20          # bottom-quintile volume threshold (T2)
HOLD = 5
FEE = 0.00045     # taker per side

DRY = "--dry-run" in sys.argv


def fetch_candles(coin):
    now_ms = int(time.time() * 1000)
    payload = json.dumps({"type": "candleSnapshot", "req": {
        "coin": coin, "interval": "1d",
        "startTime": now_ms - FETCH_DAYS * DAY_MS,
        "endTime": now_ms}}).encode()
    req = urllib.request.Request(URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def pct(a, q):
    a = sorted(a)
    if not a:
        return None
    if len(a) == 1:
        return a[0]
    idx = q * (len(a) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(a) - 1)
    return a[lo] + (a[hi] - a[lo]) * (idx - lo)


def rolling_median(vals, win):
    out = []
    for i in range(len(vals)):
        lo = max(0, i - win)
        if i <= lo:
            out.append(None)
        else:
            out.append(statistics.median(vals[lo:i]))
    return out


def load_state():
    path = os.path.join(OUT, "paper_state.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"last_day": None, "pending": []}


def save_state(s):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "paper_state.json"), "w") as f:
        json.dump(s, f, indent=2)


def append_trade(row):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "paper_trades.csv")
    fresh = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if fresh:
            w.writerow(["coin", "entry_day", "exit_day", "trigger", "entry_close",
                        "exit_close", "ret_pct", "fees_pct", "net_pct", "status"])
        w.writerow(row)


def notify(level, msg):
    msg = msg.replace('"', "'")
    os.system(f'{NOTIFY} {level} "{msg}"')


def day_str(ms):
    return time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))


def main():
    state = load_state()
    now_ms = int(time.time() * 1000)
    today = day_str(now_ms)

    # close pending trades whose exit day has arrived
    closes = {}
    for coin in COINS:
        try:
            candles = fetch_candles(coin)
            if candles:
                closes[coin] = float(candles[-1]["c"])
        except Exception as e:
            print(f"fetch fail {coin}: {e}")
    for p in list(state["pending"]):
        if p["exit_day"] <= today:
            c = closes.get(p["coin"])
            if c:
                gross = (c - p["entry_close"]) / p["entry_close"] * 100
                fees = FEE * 2 * 100
                net = gross - fees
                append_trade([p["coin"], p["entry_day"], p["exit_day"], p["trigger"],
                              round(p["entry_close"], 6), round(c, 6),
                              round(gross, 3), round(fees, 3), round(net, 3), "closed"])
                state["pending"].remove(p)
                if not DRY:
                    notify("done", f"PAPER CLOSE {p['coin']} ({p['trigger']}): "
                                   f"{gross:+.2f}% gross, {net:+.2f}% net (5d)")
                print(f"CLOSED {p['coin']} {p['trigger']} gross {gross:+.2f}% net {net:+.2f}%")

    # evaluate the latest closed candle for triggers
    newest_day = state["last_day"]
    for coin in COINS:
        try:
            candles = fetch_candles(coin)
        except Exception as e:
            print(f"fetch fail {coin}: {e}")
            continue
        closed = [c for c in candles if c["t"] + DAY_MS <= now_ms]
        if len(closed) < 60:
            continue
        for c in closed:
            c["c"] = float(c["c"])
            c["v"] = float(c["v"])
        last = closed[-1]
        day = day_str(last["t"])
        if day == state["last_day"]:
            continue
        closes_s = [c["c"] for c in closed]
        prev = closes_s[-2]
        ret = (last["c"] - prev) / prev * 100
        if len(closes_s) >= SIGMA_WIN + 1:
            rets = [(closes_s[i] - closes_s[i - 1]) / closes_s[i - 1] * 100
                    for i in range(len(closes_s) - SIGMA_WIN, len(closes_s))]
            sigma = statistics.stdev(rets)
        else:
            sigma = None
        vols = [float(c["v"]) for c in closed]
        med_series = rolling_median(vols, VOL_WIN)
        med = med_series[-1]
        ratio = float(last["v"]) / med if med else None
        pairs = [(c, m) for c, m in zip(closed, med_series) if m]
        ratio_hist = [float(c["v"]) / m for c, m in pairs]
        q20 = pct(ratio_hist, Q)

        trigger = None
        if sigma and ret < -3 * sigma:
            trigger = "T1_crash"
        elif ret < 0 and ratio is not None and q20 is not None and ratio < q20:
            trigger = "T2_lowvol"

        if day > (newest_day or ""):
            newest_day = day
        if trigger and not any(p["coin"] == coin for p in state["pending"]):
            exit_day = time.strftime("%Y-%m-%d", time.gmtime(last["t"] / 1000 + HOLD * DAY_MS / 1000))
            state["pending"].append({"coin": coin, "entry_day": day, "exit_day": exit_day,
                                     "trigger": trigger, "entry_close": last["c"]})
            if not DRY:
                notify("done", f"PAPER ENTRY LONG {coin} ({trigger}): ret={ret:+.2f}% "
                               f"sigma={sigma:.2f} entry={last['c']} exit={exit_day}")
            print(f"ENTRY {coin} {trigger} day={day} ret={ret:+.2f}% entry={last['c']}")

    if not DRY:
        state["last_day"] = newest_day or state["last_day"]
        save_state(state)
    print(f"monitor done: last_day={state.get('last_day')} pending={len(state['pending'])}")


if __name__ == "__main__":
    main()
