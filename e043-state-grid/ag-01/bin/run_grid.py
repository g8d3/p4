#!/usr/bin/env python3
"""e043 — driver for range_grid.py (Fase 2-A1).

Precomputes the windowed regime EMA and ATR arrays once (e022 v2 style), then
walks bars causally through the two-sided ATR-spaced range grid.
"""

import argparse, json, math, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from range_grid import Config, RangeGrid


def ema_window_series(closes, period):
    """Cold-start windowed EMA (e022 _ema) computed causally per bar:
    val[t] = EMA over closes[max(0,t-period):t], seeded at window start."""
    n = len(closes)
    out = np.empty(n)
    alpha = 2.0 / (period + 1)
    for t in range(n):
        if t == 0:
            out[t] = closes[0]
            continue
        w0 = max(0, t - period)
        e = closes[w0]
        for c in closes[w0 + 1:t]:
            e = alpha * c + (1 - alpha) * e
        out[t] = e
    return out


def atr_series(highs, lows, closes, period):
    n = len(closes)
    out = np.zeros(n)
    for t in range(1, n):
        w0 = max(0, t - period)
        h = np.array(highs[w0:t]); l = np.array(lows[w0:t]); c = np.array(closes[w0:t])
        pc = np.roll(c, 1); pc[0] = c[0]
        tr = np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])
        out[t] = tr.mean()
    return out


def run(df, cfg, start, ema_f, ema_s, atr, out_dir=None, tag=None):
    g = RangeGrid(cfg)
    closes_hist, volumes_hist = [], []
    for i in range(start, len(df)):
        c = float(df["close"].iloc[i]); v = float(df["volume"].iloc[i])
        closes_hist.append(c); volumes_hist.append(v)
        g.step(i, float(df["high"].iloc[i]), float(df["low"].iloc[i]), c,
               atr[i - 1], ema_f[i - 1], ema_s[i - 1], closes_hist, volumes_hist, tag or "")
    eq = np.array(g.equity, dtype=float)
    sc = cfg.start_cash
    ret = (eq[-1] - sc) / sc * 100.0
    peak = np.maximum.accumulate(eq)
    dd = ((eq - peak) / peak).min() * 100.0
    rets = np.diff(eq) / eq[:-1]
    sharpe = (rets.mean() / rets.std() * math.sqrt(252) if len(rets) > 2 and rets.std() > 0 else 0.0)
    m = {"return_pct": round(ret, 4), "max_dd_pct": round(float(dd), 4),
         "sharpe": round(float(sharpe), 4), "n_fills": g.n_fills,
         "commissions": round(g.commissions, 2), "n_rebalances": g.n_rebalances,
         "n_regime_flips": g.n_regime_flips, "n_liquidations": g.n_liquidations,
         "n_cap_enforcements": g.n_cap_enforcements,
         "realized_pnl": round(g.realized, 2), "final_equity": round(float(eq[-1]), 2)}
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        json.dump(m, open(f"{out_dir}/metrics.json", "w"), indent=2)
        pd.DataFrame({"i": list(range(len(g.equity))), "equity": g.equity}).to_csv(
            f"{out_dir}/equity_curve.csv", index=False)
        pd.DataFrame(g.fills, columns=["bar", "side", "px", "notional", "fee", "kind"]).to_csv(
            f"{out_dir}/fills_report.csv", index=False)
    return g, m


def load(df, cfg, start):
    closes = df["close"].astype(float).values
    highs = df["high"].astype(float).values
    lows = df["low"].astype(float).values
    ema_f = ema_window_series(closes, cfg.trend_fast)
    ema_s = ema_window_series(closes, cfg.trend_slow)
    atr = atr_series(highs, lows, closes, cfg.atr_period)
    return ema_f, ema_s, atr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out-dir", default="output/range_default")
    ap.add_argument("--start", type=int, default=400)
    ap.add_argument("--budget", type=float, default=30_000)
    ap.add_argument("--atr-mult", type=float, default=1.5)
    ap.add_argument("--levels", type=int, default=3)
    ap.add_argument("--rebalance", type=int, default=96)
    ap.add_argument("--max-exposure-mult", type=float, default=3.0)
    ap.add_argument("--trend-fast", type=int, default=20)
    ap.add_argument("--trend-slow", type=int, default=100)
    ap.add_argument("--trend-enter", type=float, default=0.5)
    ap.add_argument("--trend-exit", type=float, default=0.2)
    ap.add_argument("--liquidation-mult", type=float, default=1.0)
    ap.add_argument("--min-order", type=float, default=500)
    ap.add_argument("--max-order", type=float, default=10_000)
    args = ap.parse_args()

    cfg = Config(budget=args.budget, atr_mult=args.atr_mult, max_levels=args.levels,
                 rebalance=args.rebalance, max_exposure_mult=args.max_exposure_mult,
                 trend_fast=args.trend_fast, trend_slow=args.trend_slow,
                 trend_enter=args.trend_enter / 100.0, trend_exit=args.trend_exit / 100.0,
                 liquidation_mult=args.liquidation_mult,
                 min_order=args.min_order, max_order=args.max_order)
    df = pd.read_csv(args.data)
    ema_f, ema_s, atr = load(df, cfg, args.start)
    g, m = run(df, cfg, args.start, ema_f, ema_s, atr, out_dir=args.out_dir,
               tag=os.path.basename(args.data))
    print(json.dumps(m, indent=2))


if __name__ == "__main__":
    main()
