#!/usr/bin/env python3
"""Phase 4a — intrabar fill realism test.

The 2h strategy evaluated on 5m bars: signals/ATR computed on 2h closes,
but trail arming/fills step through 5m extremes inside each 2h bar.
This resolves the "optimistic same-bar fill" question: does the edge
survive when the intrabar sequence is NOT assumed favorable-first?

Usage: python3 bin/intrabar.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bin.backtest import add_indicators, load

MULT = 0.02
EMA_LEN = 5
COMMISSION = 0.0005
LEVERAGE = 1
START = 10_000.0


def run_intrabar(h2, m5, start_cap=START, commission=COMMISSION, signal="cross"):
    h2 = add_indicators(h2.copy(), EMA_LEN, 14, "daily")
    h2["bar"] = range(len(h2))
    m5 = m5.copy()
    m5["bucket"] = m5["ts"].dt.floor("2h")
    h2["bucket"] = h2["ts"].dt.floor("2h")
    merged = m5.merge(h2[["bucket", "ema", "vwap", "atr", "c", "bar"]],
                      on="bucket", how="left", suffixes=("", "_2h"))

    equity = start_cap
    trades = []
    pos = 0
    stop = np.inf
    armed = False
    entry_price = np.nan
    entry_bar_idx = -1

    g = merged.groupby("bar", dropna=True)
    for bar_id, grp in g:
        if np.isnan(grp["atr"].iloc[0]):
            continue
        ema_i = grp["ema"].iloc[0]
        vwap_i = grp["vwap"].iloc[0]
        T = grp["atr"].iloc[0] * MULT
        # signal at previous 2h close == first 5m bar of this bucket
        prev_ema = grp["ema"].iloc[0]
        if bar_id == 0:
            prev_ema, prev_vwap = np.nan, np.nan
        else:
            prev_ema = h2.iloc[bar_id - 1]["ema"]
            prev_vwap = h2.iloc[bar_id - 1]["vwap"]
        if signal == "zscore":
            sma = h2["c"].rolling(100).mean()
            sd = h2["c"].rolling(100).std(ddof=0)
            z_cur = (grp["c_2h"].iloc[0] - sma.iloc[bar_id]) / sd.iloc[bar_id]
            long_sig = not np.isnan(z_cur) and z_cur > 2
            short_sig = not np.isnan(z_cur) and z_cur < -2
        elif pos == 0 and not np.isnan(prev_ema) and not np.isnan(prev_vwap):
            long_sig = prev_ema < prev_vwap and ema_i >= vwap_i
            short_sig = prev_ema > prev_vwap and ema_i <= vwap_i
        else:
            long_sig = short_sig = False
        if pos == 0 and long_sig:
            pos = 1; entry_price = grp["c_2h"].iloc[0]
            armed = False; stop = np.inf
            entry_bar_idx = bar_id
        elif pos == 0 and short_sig:
            pos = -1; entry_price = grp["c_2h"].iloc[0]
            armed = False; stop = np.inf
            entry_bar_idx = bar_id
        # entry fills at bucket CLOSE -> the trail may only act from the NEXT bucket
        pos_walk = pos != 0 and bar_id > entry_bar_idx
        # walk the 5m path inside this 2h bar
        exit_px = None
        for row in grp.itertuples():
            if pos == 0 or not pos_walk:
                break
            h_, l_, o_, c_ = row.h, row.l, row.o, row.c
            wasA = armed
            if pos == 1:
                if not armed and h_ >= entry_price + T:
                    armed = True; stop = h_ - T
                elif armed:
                    stop = max(stop, h_ - T)
                if armed and l_ <= stop:
                    exit_px = (o_ if (wasA and o_ < stop) else stop)
                    break
            else:
                if not armed and l_ <= entry_price - T:
                    armed = True; stop = l_ + T
                elif armed:
                    stop = min(stop, l_ + T)
                if armed and h_ >= stop:
                    exit_px = (o_ if (wasA and o_ > stop) else stop)
                    break
        if exit_px is not None:
            notional = LEVERAGE * equity
            pnl = notional * (exit_px - entry_price) / entry_price * pos - 2 * commission * notional
            equity += pnl
            trades.append({"bar": bar_id, "side": "L" if pos == 1 else "S",
                           "entry_px": round(entry_price, 2), "exit_px": round(exit_px, 2),
                           "pnl_usd": round(pnl, 2), "equity": round(equity, 2)})
            pos = 0
        # reversal at 2h close
        if pos != 0:
            c_2h = grp["c_2h"].iloc[0]
            if pos == 1 and (prev_ema > prev_vwap and ema_i <= vwap_i):
                pass  # handled next bucket as new entry? (simplified: close here)
            if pos == 1 and prev_ema > prev_vwap and ema_i <= vwap_i:
                notional = LEVERAGE * equity
                pnl = notional * (c_2h - entry_price) / entry_price - 2 * commission * notional
                equity += pnl
                trades.append({"bar": bar_id, "side": "L", "entry_px": round(entry_price, 2),
                               "exit_px": round(c_2h, 2), "pnl_usd": round(pnl, 2),
                               "equity": round(equity, 2)})
                pos = 0
            elif pos == -1 and prev_ema < prev_vwap and ema_i >= vwap_i:
                notional = LEVERAGE * equity
                pnl = notional * (c_2h - entry_price) / entry_price * -1 - 2 * commission * notional
                equity += pnl
                trades.append({"bar": bar_id, "side": "S", "entry_px": round(entry_price, 2),
                               "exit_px": round(c_2h, 2), "pnl_usd": round(pnl, 2),
                               "equity": round(equity, 2)})
                pos = 0
    if pos != 0:
        c_last = h2["c"].iloc[-1]
        notional = LEVERAGE * equity
        pnl = notional * (c_last - entry_price) / entry_price * pos - 2 * commission * notional
        equity += pnl
        trades.append({"bar": len(h2) - 1, "side": "L" if pos == 1 else "S",
                       "entry_px": round(entry_price, 2), "exit_px": round(c_last, 2),
                       "pnl_usd": round(pnl, 2), "equity": round(equity, 2)})
    tdf = pd.DataFrame(trades)
    days = max(1.0, (h2["ts"].iloc[-1] - h2["ts"].iloc[0]).total_seconds() / 86400)
    gp = tdf[tdf.pnl_usd > 0].pnl_usd.sum()
    gl = -tdf[tdf.pnl_usd <= 0].pnl_usd.sum()
    pf = round(gp / gl, 2) if gl > 0 else None
    net = equity / start_cap - 1
    eqc = start_cap + tdf.pnl_usd.cumsum()
    dd = round(100 * float(((eqc - eqc.cummax()) / eqc.cummax()).min()), 2)
    return {"trades": len(tdf), "per_day": round(((1 + net) ** (1 / days) - 1) * 100, 4),
            "pf": pf, "net_pct": round(net * 100, 1), "dd_pct": dd}


def main():
    h2 = load("output/btcusdt_2h.csv")
    m5 = load("output/btcusdt_5m.csv")
    res = {}
    for win in ("2024-08-01:2026-04-30", "2026-05-01:2026-08-22"):
        a, b = win.split(":")
        h2w = h2[(h2["ts"] >= pd.Timestamp(a, tz="UTC")) &
                 (h2["ts"] < pd.Timestamp(b, tz="UTC"))].reset_index(drop=True)
        m5w = m5[(m5["ts"] >= pd.Timestamp(a, tz="UTC")) &
                 (m5["ts"] < pd.Timestamp(b, tz="UTC"))].reset_index(drop=True)
        r = run_intrabar(h2w, m5w)
        res[win] = r
        print(f"INTRABAR 5m fills  window={win}: {r}")
    json.dump(res, open("output/intrabar.json", "w"), indent=1)


if __name__ == "__main__":
    main()
