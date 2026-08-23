#!/usr/bin/env python3
"""Phase 8 — synthetic-data negative control.

Generate price series that mimic BTC daily stats (vol/momentum) but are
pure noise (geometric random walk, drift = 0 and drift = real-sample drift),
then run the EMA7/0.02 daily machinery on them. If the machine prints
profits on noise, that is conclusive evidence that the trailing machine
harvests drift, not signal.

Usage: python3 bin/synthetic_null.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bin.backtest import load, run

N_SERIES = 60
SEED = 11


def real_stats(df):
    r = np.log(df["c"].to_numpy() / df["c"].shift(1).to_numpy())
    r = r[~np.isnan(r)]
    return float(r.mean()), float(r.std()), float(df["c"].iloc[-1])


def synth_frame(seed, n=760, start=30_000.0, mu=0.0, sigma=0.03):
    rng = np.random.default_rng(seed)
    rets = rng.normal(mu, sigma, n)
    close = start * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0, sigma / 3, n)))
    low = close * (1 - np.abs(rng.normal(0, sigma / 3, n)))
    o = np.concatenate([[start], close[:-1]])
    vol = np.abs(rng.normal(1.0, 0.3, n)) + 0.1
    ts = pd.date_range("2024-08-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame({"ts": ts, "o": o, "h": np.maximum(high, np.maximum(o, close)),
                         "l": np.minimum(low, np.minimum(o, close)),
                         "c": close, "v": vol})


def one(df):
    trades, eq, start, _ = run(df, ema_len=7, atr_mult=0.02, commission=0.0005,
                               vwap_mode="weekly")
    tdf = pd.DataFrame(trades)
    if not len(tdf):
        return None
    gp = tdf[tdf.pnl_usd > 0].pnl_usd.sum()
    gl = -tdf[tdf.pnl_usd <= 0].pnl_usd.sum()
    net = eq / start - 1
    days = (df["ts"].iloc[-1] - df["ts"].iloc[0]).total_seconds() / 86400
    return {"pf": round(gp / gl, 2) if gl > 0 else None,
            "per_day": round(((1 + net) ** (1 / days) - 1) * 100, 4),
            "trades": len(tdf)}


def main():
    btc = load("output/btcusdt_1d_full.csv")
    mu, sigma, last = real_stats(btc)
    print(f"real BTC daily log-return: mu={mu*100:.3f}%/day, sigma={sigma*100:.2f}%/day")
    out = {"real": one(btc), "trials": [], "note": "negative control: pure noise series"}

    for drift_name, mu_in in (("zero_drift", 0.0), ("real_drift", mu)):
        pfs, pds, wins = [], [], 0
        for i in range(N_SERIES):
            df = synth_frame(SEED + i, mu=mu_in, sigma=sigma)
            r = one(df)
            if r is None:
                continue
            pfs.append(r["pf"])
            pds.append(r["per_day"])
            if r["per_day"] > 0:
                wins += 1
        out["trials"].append({
            "drift": drift_name, "n": len(pfs),
            "median_pf": round(float(np.median(pfs)), 2),
            "pf_p05": round(float(np.percentile(pfs, 5)), 2),
            "pf_p95": round(float(np.percentile(pfs, 95)), 2),
            "median_per_day": round(float(np.median(pds)), 4),
            "positive_fraction": round(wins / len(pds), 3),
        })
        t = out["trials"][-1]
        print(f"  {drift_name:12}: median PF {t['median_pf']} (p05 {t['pf_p05']}, p95 {t['pf_p95']}),"
              f" med %/day {t['median_per_day']}, {t['positive_fraction']:.0%} positive")
    print(f"\nREAL BTC 1d (bar-level): PF {out['real']['pf']} {out['real']['per_day']}%/day")
    json.dump(out, open("output/synthetic_null.json", "w"), indent=1)
    print("saved -> output/synthetic_null.json")


if __name__ == "__main__":
    main()
