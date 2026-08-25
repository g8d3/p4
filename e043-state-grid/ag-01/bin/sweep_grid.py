#!/usr/bin/env python3
"""e043 — small sweep over the range-grid base (Fase 2-A1). Precomputed EMAs."""

import argparse, math, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from range_grid import Config, RangeGrid
from run_grid import ema_window_series, atr_series, run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="output/range_sweep.csv")
    ap.add_argument("--start", type=int, default=400)
    ap.add_argument("--budget", type=float, default=30_000)
    ap.add_argument("--trend-fast", type=int, default=20)
    ap.add_argument("--trend-slow", type=int, default=100)
    args = ap.parse_args()
    df = pd.read_csv(args.data)
    closes = df["close"].astype(float).values
    highs = df["high"].astype(float).values
    lows = df["low"].astype(float).values
    ema_f = ema_window_series(closes, args.trend_fast)
    ema_s = ema_window_series(closes, args.trend_slow)
    atr = atr_series(highs, lows, closes, 14)

    rows = []
    for atr_mult in [1.5, 2.0, 2.5]:
        for levels in [2, 3]:
            for reb in [96, 192]:
                for ent in [0.3, 0.5, 0.8]:
                    for cap in [3, 4]:
                        cfg = Config(budget=args.budget, atr_mult=atr_mult,
                                     max_levels=levels, rebalance=reb,
                                     max_exposure_mult=cap,
                                     trend_fast=args.trend_fast,
                                     trend_slow=args.trend_slow,
                                     trend_enter=ent / 100.0,
                                     trend_exit=max(0.2, ent / 2) / 100.0)
                        g, m = run(df, cfg, args.start, ema_f, ema_s, atr,
                                   tag=f"e{ent}")
                        rows.append(dict(atr=atr_mult, lv=levels, reb=reb, ent=ent,
                                         cap=cap, **m))
                        print(f"atr{atr_mult} lv{levels} reb{reb} e{ent} cap{cap} "
                              f"-> {m['return_pct']:7.2f}% dd={m['max_dd_pct']:6.2f} "
                              f"fills={m['n_fills']:4d} flips={m['n_regime_flips']:4d}",
                              flush=True)
    out = pd.DataFrame(rows).sort_values("return_pct", ascending=False)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    out.to_csv(args.out, index=False)
    print("\nWrote", args.out)
    print(out.head(8).to_string(index=False))


if __name__ == "__main__":
    main()
