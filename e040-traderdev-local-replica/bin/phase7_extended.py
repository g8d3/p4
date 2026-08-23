#!/usr/bin/env python3
"""Phase 7 — extended 1d analysis.

1. Full-history 1d (2023-01 -> 2026-08): regime robustness + 3x sample.
2. Param sweep: EMA {3,5,7,9} x mult {0.01,0.02,0.05,0.1} (bar-level).
3. Maker scenario: fee 0 / fee 0 + tiny slip on the best configs.
4. Intrabar validation of the strongest configs on 5m (BTC/ETH when ready).

Usage: python3 bin/phase7_extended.py
"""
import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bin.backtest import load, run

WIN_FULL = "2023-01-01:2026-08-22"
WINDOWS = {"pre_2023_24": "2023-01-01:2024-07-31",
           "in_2024_26": "2024-08-01:2026-04-30",
           "oos_2026": "2026-05-01:2026-08-22"}


def metrics_of(trades, eq, start, days):
    tdf = pd.DataFrame(trades)
    gp = tdf[tdf.pnl_usd > 0].pnl_usd.sum()
    gl = -tdf[tdf.pnl_usd <= 0].pnl_usd.sum()
    pf = round(gp / gl, 2) if gl > 0 else None
    net = eq / start - 1
    eqc = start + tdf.pnl_usd.cumsum()
    dd = round(100 * float(((eqc - eqc.cummax()) / eqc.cummax()).min()), 2)
    per_day = round(((1 + net) ** (1 / max(1.0, days)) - 1) * 100, 4)
    return {"trades": len(tdf), "per_day": per_day, "pf": pf, "dd": dd,
            "net_pct": round(net * 100, 1)}


def run_window(df, window, ema=5, mult=0.02, commission=0.0005, slip=0.0,
               vwap="weekly"):
    d = df.copy()
    a, b = window.split(":")
    d = d[(d["ts"] >= pd.Timestamp(a, tz="UTC")) &
          (d["ts"] < pd.Timestamp(b, tz="UTC"))].reset_index(drop=True)
    if len(d) < 40:
        return None
    trades, eq, start, _ = run(d, ema_len=ema, atr_mult=mult,
                               commission=commission, slippage=slip,
                               vwap_mode=vwap)
    days = (d["ts"].iloc[-1] - d["ts"].iloc[0]).total_seconds() / 86400
    return metrics_of(trades, eq, start, days)


def main():
    out = {}
    print("═══ 1. FULL-HISTORY (Bybit 1d, weekly VWAP, EMA5/0.02) ═══")
    for coin in ("BTC", "ETH", "SOL"):
        df = load(f"output/{coin.lower()}usdt_1d_full.csv")
        out.setdefault("full_history", {})[coin] = {}
        for name, w in {"full": WIN_FULL, **WINDOWS}.items():
            r = run_window(df, w)
            out["full_history"][coin][name] = r
            if r:
                print(f"  {coin} {name:12}: tr={r['trades']:>4} %/day={r['per_day']} PF={r['pf']} DD={r['dd']}")
            else:
                print(f"  {coin} {name:12}: too few bars")

    print("\n═══ 2. PARAM SWEEP (Bybit BTC 1d, full window, bar-level) ═══")
    dfb = load("output/btcusdt_1d_full.csv")
    sweep = out.setdefault("sweep", {})
    for ema in (3, 5, 7, 9):
        for mult in (0.01, 0.02, 0.05, 0.1):
            r = run_window(dfb, WIN_FULL, ema=ema, mult=mult)
            sweep[f"ema{ema}_m{mult}"] = r
            print(f"  ema={ema} mult={mult:.2f}: tr={r['trades']:>4} %/day={r['per_day']} PF={r['pf']} DD={r['dd']}")

    print("\n═══ 3. MAKER SCENARIO (fee 0; fee 0 + 3bps slip) on BTC 1d full ═══")
    maker = out.setdefault("maker", {})
    for ema, mult in ((5, 0.02), (7, 0.02), (5, 0.05)):
        for tag, comm, slip in (("fee0", 0.0, 0.0), ("fee0_slip3bps", 0.0, 0.0003)):
            r = run_window(dfb, WIN_FULL, ema=ema, mult=mult,
                           commission=comm, slip=slip)
            maker[f"ema{ema}_m{mult}_{tag}"] = r
            print(f"  ema={ema} mult={mult:.2f} {tag:14}: tr={r['trades']:>4} %/day={r['per_day']} PF={r['pf']} DD={r['dd']}")

    json.dump(out, open("output/phase7.json", "w"), indent=1)
    print("\nsaved -> output/phase7.json")


if __name__ == "__main__":
    main()
