#!/usr/bin/env python3
"""Paper monitor for the TSMR + vol-targeting strategy (Phase 11 survivor).

Rules (same as bin/phase11_tsmr.py, L=30, majors):
- Weekly rebalance at the last CLOSED daily candle of each week.
- Signal per coin: 30-day return > 0 -> long at vol-targeted weight
  (target 20% annualized, 30d realized vol), else flat. Equal allocation.
- Daily mark-to-market at closes; state in output/tsmr_paper_state.json;
  phone notifications on rebalances; log trades tsmr_paper_*.csv.

Run daily 00:30 UTC via cron (bin/paper_tsmr_cron.sh).
"""
import csv
import json
import os
import sys
import time
import urllib.request

import numpy as np
import pandas as pd

URL = "https://api.hyperliquid.xyz/info"
DAY_MS = 86_400_000
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "output")
NOTIFY = os.path.join(ROOT, "..", "e000-fundamentals", "bin", "notify.sh")

COINS = ["BTC", "ETH", "SOL", "XRP", "DOGE"]
FETCH_DAYS = 420
L = 30
TARGET_VOL = 0.20 / np.sqrt(365)
FEE = 0.00035
START_EQUITY = 30_000.0
DRY = "--dry-run" in sys.argv


def fetch(coin):
    now = int(time.time() * 1000)
    payload = json.dumps({"type": "candleSnapshot", "req": {
        "coin": coin, "interval": "1d",
        "startTime": now - FETCH_DAYS * DAY_MS, "endTime": now}}).encode()
    req = urllib.request.Request(URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def load_closes():
    df = pd.DataFrame()
    for coin in COINS:
        raw = fetch(coin)
        s = pd.Series({r["t"]: float(r["c"]) for r in raw})
        s.index = pd.to_datetime(s.index, unit="ms", utc=True)
        df = pd.concat([df, s.rename(coin)], axis=1)
    return df.sort_index()


def signals_and_weights(m):
    rets = m.pct_change()
    vol = rets.rolling(30).std()
    mom = (m.pct_change(L) > 0).astype(float)
    w = (TARGET_VOL / vol).clip(upper=1.0).fillna(0.0)
    w = (w * mom).fillna(0.0) / w.shape[1]
    return mom, w


def load_state():
    p = os.path.join(OUT, "tsmr_paper_state.json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return {"equity": START_EQUITY, "weights": {c: 0.0 for c in COINS},
            "nav_hist": [], "trades": [], "last_week": None}


def save_state(s):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "tsmr_paper_state.json"), "w") as f:
        json.dump(s, f, indent=2, default=str)


def notify(level, msg):
    os.system(f'{NOTIFY} {level} "{msg.replace(chr(34), chr(39))}"')


def main():
    if DRY:
        print("DRY-RUN")
    m = load_closes()
    state = load_state()
    if len(m) < L + 60 or m.shape[1] < len(COINS):
        notify("error", "e040 tsmr paper: insufficient data")
        return
    # last CLOSED day: exclude the current (incomplete) day
    today = pd.Timestamp.now(tz="UTC").normalize() + pd.Timedelta(days=1)
    closed = m[m.index < today]
    last = closed.index[-1]
    # idempotent per processed day: a second run the same day (manual, or the
    # @reboot catch-up after the PC was off) must not re-apply the day's return
    # (that would double-compound the same move). Skip if the day is already
    # in nav_hist.
    if state.get("nav_hist") and str(last.date()) == state["nav_hist"][-1]["date"]:
        print(f"already processed {last.date()}, skipping")
        return
    week = last.to_period("W")
    mom, w = signals_and_weights(closed)
    w_reb = w.iloc[-1]
    closes_now = closed.iloc[-1]

    nav = state["equity"]
    if str(week) != state.get("last_week"):
        # rebalance at last close -> apply weights (no daily friction modeling
        # beyond taker fee on changed legs)
        prev = pd.Series(state.get("weights", {c: 0.0 for c in COINS}),
                         index=COINS)
        turn = float((w_reb - prev).abs().sum()) / 2.0
        cost = turn * FEE * 2.0 * nav
        nav -= cost
        changed = (w_reb - prev).abs() > 0.01
        if changed.any():
            legs = ", ".join(f"{c}{'L' if w_reb[c] > 0 else 'F'}" for c in COINS if changed[c])
            state["trades"].append({"week": str(week), "date": str(last.date()),
                                    "legs": legs, "cost_usd": round(cost, 2)})
            notify("done", f"e040 tsmr REBALANCE wk{week} {legs} cost ${cost:.2f}")
        state["equity"] = nav
        state["weights"] = {c: float(v) for c, v in w_reb.items()}
        state["last_week"] = str(week)

    # mark to market daily
    longs = {c: state["weights"].get(c, 0.0) for c in COINS}
    if any(v > 0 for v in longs.values()):
        px = {c: float(closes_now[c]) for c in COINS}
        # store prev marks implicitly: keep simple const weights nav update
        prev_t = closed.index[-2]
        rets = (closed.iloc[-1] / closed.iloc[-2]) - 1
        port_ret = sum(longs[c] * float(rets[c]) for c in COINS) / len(COINS)
        state["equity"] *= (1 + port_ret)
        # note: weights are not re-marked daily (weekly strategy) — acceptable.
    state["nav_hist"].append({"date": str(last.date()), "nav": round(state["equity"], 2)})
    if not DRY:
        save_state(state)
    print(f"nav={state['equity']:.2f} week={state['last_week']} "
          f"weights={ {k: round(v, 3) for k, v in state['weights'].items() if v > 0} }")


if __name__ == "__main__":
    main()
