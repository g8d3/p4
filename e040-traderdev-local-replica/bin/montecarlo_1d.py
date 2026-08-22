#!/usr/bin/env python3
"""Monte Carlo robustness of the 1-day intrabar version (Phase 6).

Questions:
1. Is the realized path stable when trade ORDER is reshuffled?
   -> p(ending negative), equity & DD percentiles (10k paths).
2. Block bootstrap (3-trade blocks) to respect short-range dependence.
3. What does adding a stop loss (clip per-trade loss at 2/5/10% of equity)
   do to the distribution?

Usage: python3 bin/montecarlo_1d.py
"""
import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

N = 10_000
SEED = 7


def mc(returns, n=N, seed=SEED, block=1, start=10_000.0, loss_cap=None):
    rng = np.random.default_rng(seed)
    r = np.asarray(returns, dtype=float)
    if loss_cap is not None:
        r = np.maximum(r, -loss_cap)
    n_t = len(r)
    finals = np.empty(n)
    dds = np.empty(n)
    for i in range(n):
        if block > 1:
            nb = int(np.ceil(n_t / block))
            idx = np.concatenate([rng.integers(0, n_t, size=block)
                                  for _ in range(nb)])[:n_t]
        else:
            idx = rng.integers(0, n_t, size=n_t)
        eq = start * np.cumprod(1 + r[idx])
        full = np.concatenate([[start], eq])
        peak = np.maximum.accumulate(full)
        finals[i] = eq[-1]
        dds[i] = ((full - peak) / peak).min()
    return {
        "p_negative": round(float((finals < start).mean()), 4),
        "final_equity_median": round(float(np.median(finals)), 2),
        "final_p05": round(float(np.percentile(finals, 5)), 2),
        "final_p95": round(float(np.percentile(finals, 95)), 2),
        "dd_median": round(100 * float(np.median(dds)), 2),
        "dd_p05": round(100 * float(np.percentile(dds, 5)), 2),
        "dd_p95": round(100 * float(np.percentile(dds, 95)), 2),
    }


def main():
    spec = importlib.util.spec_from_file_location("p5mod", os.path.join(ROOT, "bin", "phase5_daily_weekly.py"))
    p5 = importlib.util.module_from_spec(spec)
    sys.modules["p5mod"] = p5
    spec.loader.exec_module(p5)
    from bin.backtest import load

    out = {}
    for coin, csv1, csv5 in [("BTC", "output/btcusdt_1d.csv", "output/btcusdt_5m.csv"),
                             ("ETH", "output/ethusdt_1d.csv", "output/ethusdt_5m.csv")]:
        h1d = load(csv1)
        m5 = load(csv5)
        m5 = m5[(m5["ts"] >= pd.Timestamp("2024-08-01", tz="UTC")) &
                (m5["ts"] < pd.Timestamp("2026-08-22", tz="UTC"))].reset_index(drop=True)
        r = p5.intrabar_daily(h1d, m5, mult=0.02)
        rets = r.pop("returns_", [])
        print(f"═══════ {coin} 1d intrabar: trades={r['trades']} PF={r['pf']} "
              f"%/day={r['per_day']} DD={r['dd']} ═══════")
        for label, kw in [("reshuffle (iid)", dict(block=1)),
                          ("blocks of 3", dict(block=3))]:
            m = mc(rets, **kw)
            out[f"{coin}_{label}"] = m
            print(f"  {label:16} p(neg)={m['p_negative']} med_equity={m['final_equity_median']:.0f} "
                  f"(p05={m['final_p05']:.0f}, p95={m['final_p95']:.0f}) "
                  f"DD med={m['dd_median']}% p05={m['dd_p05']}%")
        for cap in (0.02, 0.05, 0.10):
            m = mc(rets, loss_cap=cap)
            out[f"{coin}_stop_loss_{cap}"] = m
            print(f"  SL cap {cap*100:>4.0f}%  p(neg)={m['p_negative']} med_eq={m['final_equity_median']:.0f} "
                  f"DD med={m['dd_median']}% p05={m['dd_p05']}%")
    json.dump(out, open("output/mc_1d.json", "w"), indent=1)
    print("\nsaved -> output/mc_1d.json")


if __name__ == "__main__":
    main()
