#!/usr/bin/env python3
"""Paper-trade monitor for the e040 1-day EMA-VWAP micro-trail strategy.

Runs daily via cron (00:15 UTC). For each coin:
  1. Fetch 1d candles (trailing 90 days) from Hyperliquid candleSnapshot.
  2. Compute EMA5, weekly-anchored VWAP, ATR14.
  3. Signal at the last CLOSED day: crossover(ema, vwap) -> enter at that
     close; crossunder -> close at close (reversal).
  4. Trail only (NO stop loss, as designed): arm when high >= entry + T,
     stop = best - T (long), exit when low <= stop (gap -> open).
     T = ATR * 0.02. Sizing 1x, fee 0.05% per side, start 10k per coin.
  5. Phone via e000-fundamentals/bin/notify.sh on every open/close.

Idempotent per (coin, day): state in output/paper_state.json; each closed
daily candle processed once. Reality check vs backtest is the point of
this file — deviations get recorded too.

Run: zsh -c 'cd <exp> && python3 bin/paper_1d.py'   (zsh loads env vars)
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

COINS = ["BTC", "ETH", "SOL"]
FETCH_DAYS = 120
EMA_LEN = 5
ATR_LEN = 14
MULT = 0.02
FEE = 0.0005       # per side (same as backtest)
START_EQUITY = 10_000.0

DRY = "--dry-run" in sys.argv


def fetch_candles(coin, days=FETCH_DAYS):
    now_ms = int(time.time() * 1000)
    payload = json.dumps({"type": "candleSnapshot", "req": {
        "coin": coin, "interval": "1d",
        "startTime": now_ms - days * DAY_MS, "endTime": now_ms}}).encode()
    req = urllib.request.Request(URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def to_df(candles):
    df = pd.DataFrame(candles)
    df["ts"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    df = df[["ts", "o", "h", "l", "c", "v"]].sort_values("ts").reset_index(drop=True)
    for col in ("o", "h", "l", "c", "v"):
        df[col] = pd.to_numeric(df[col])
    df["ema"] = df["c"].ewm(span=EMA_LEN, adjust=False).mean()
    df["tr"] = np.maximum(
        df["h"] - df["l"],
        np.maximum((df["h"] - df["c"].shift()).abs(),
                   (df["l"] - df["c"].shift()).abs()))
    df["atr"] = df["tr"].ewm(alpha=1 / ATR_LEN, adjust=False).mean()
    wk = df["ts"].dt.to_period("W").dt.to_timestamp()
    pv = (df["c"] * df["v"]).groupby(wk).cumsum()
    vv = df["v"].groupby(wk).cumsum()
    df["vwap"] = np.where(vv > 0, pv / vv, np.nan)
    return df


def load_state():
    p = os.path.join(OUT, "paper_state.json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return {"accounts": {"BTC": {"equity": START_EQUITY, "pos": None},
                         "ETH": {"equity": START_EQUITY, "pos": None},
                         "SOL": {"equity": START_EQUITY, "pos": None}}}


def save_state(s):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "paper_state.json"), "w") as f:
        json.dump(s, f, indent=2)


def run_day(coin, acc, today):
    daily = fetch_candles(coin)
    if len(daily) < 40:
        return None
    df = to_df(daily)
    last = df.iloc[-1]
    if last["ts"].date().isoformat() == today:
        last_closed = df.iloc[-2]
    else:
        last_closed = last
    day = last_closed["ts"].date().isoformat()
    if acc.get("last_day") == day:
        return None
    i = df.index[df["ts"] == last_closed["ts"]][0]
    if i < 1 or np.isnan(df.atr.iloc[i]) or np.isnan(df.vwap.iloc[i]):
        return None
    c, h, l, o = last_closed["c"], last_closed["h"], last_closed["l"], last_closed["o"]
    ema_i, vwap_i = df.ema.iloc[i], df.vwap.iloc[i]
    prev_ema, prev_vwap = df.ema.iloc[i - 1], df.vwap.iloc[i - 1]
    T = df.atr.iloc[i] * MULT
    pos = acc.get("pos")
    events = []

    if pos:
        # 1) trail exit (closed-day bar)
        exit_px = None
        if pos["side"] == "L":
            if not pos["armed"] and h >= pos["entry_px"] + T:
                pos["armed"] = True
                pos["stop"] = h - T
            elif pos["armed"]:
                pos["stop"] = max(pos["stop"], h - T)
            if pos["armed"] and l <= pos["stop"]:
                exit_px = pos["stop"] if o >= pos["stop"] else o
        else:
            if not pos["armed"] and l <= pos["entry_px"] - T:
                pos["armed"] = True
                pos["stop"] = l + T
            elif pos["armed"]:
                pos["stop"] = min(pos["stop"], l + T)
            if pos["armed"] and h >= pos["stop"]:
                exit_px = pos["stop"] if o <= pos["stop"] else o
        if exit_px is not None:
            events.append(close_out(coin, acc, pos, exit_px, day, "trail"))
        # 2) reversal at close
        elif pos and ((pos["side"] == "L" and prev_ema > prev_vwap and ema_i <= vwap_i) or
                      (pos["side"] == "S" and prev_ema < prev_vwap and ema_i >= vwap_i)):
            events.append(close_out(coin, acc, pos, c, day, "reversal"))

    pos = acc.get("pos")
    long_sig = prev_ema < prev_vwap and ema_i >= vwap_i
    short_sig = prev_ema > prev_vwap and ema_i <= vwap_i
    if pos is None and (long_sig or short_sig):
        acc["pos"] = {"side": "L" if long_sig else "S", "entry_px": float(c),
                      "entry_day": day, "armed": False, "stop": None}
        events.append(("open", acc["pos"]["side"], float(c), day,
                       acc["pos"]["entry_px"], None, None, None))
        notify("info", f"e040 paper OPEN {coin} {acc['pos']['side']} @{float(c):.2f} ({day})")
    acc["last_day"] = day
    return events


def close_out(coin, acc, pos, exit_px, day, reason):
    notional = acc["equity"]
    pnl = notional * (exit_px - pos["entry_px"]) / pos["entry_px"] * (1 if pos["side"] == "L" else -1)
    pnl -= 2 * FEE * notional
    acc["equity"] += pnl
    ret = pnl / notional
    row = [coin, pos["entry_day"], day, pos["side"], reason,
           round(pos["entry_px"], 2), round(exit_px, 2),
           round(ret * 100, 3), "open" if False else "closed"]
    append_trade(row)
    notify("done", f"e040 paper CLOSE {coin} {pos['side']} {reason} net {ret*100:+.2f}% "
                   f"eq {acc['equity']:.0f}")
    acc["pos"] = None
    return ("close", coin, pos["side"], exit_px, day, reason)


def append_trade(row):
    path = os.path.join(OUT, "paper_trades_1d.csv")
    fresh = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if fresh:
            w.writerow(["coin", "entry_day", "exit_day", "side", "reason",
                        "entry_px", "exit_px", "net_pct", "status"])
        w.writerow(row)


def notify(level, msg):
    msg = msg.replace('"', "'")
    os.system(f'{NOTIFY} {level} "{msg}"')


def main():
    if DRY:
        print("DRY-RUN (no state write)")
    state = load_state()
    today = time.strftime("%Y-%m-%d", time.gmtime(time.time()))
    for coin in COINS:
        acc = state["accounts"].setdefault(
            coin, {"equity": START_EQUITY, "pos": None, "last_day": None})
        try:
            run_day(coin, acc, today)
        except Exception as e:
            notify("error", f"e040 paper {coin} failed: {e}")
    if not DRY:
        save_state(state)
    for coin, acc in state["accounts"].items():
        print(f"{coin}: eq={acc['equity']:.0f} pos={acc.get('pos') and acc['pos']['side']}")


if __name__ == "__main__":
    main()
