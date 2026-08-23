#!/usr/bin/env python3
"""Phase 11 — time-series momentum (TSMR) screen.

Per-coin rule (no cross-section): at each weekly rebalance, if the coin's
L-day return > 0 -> long at weight w (vol-targeted), else flat. Ranks
within the universe don't matter; the signal is absolute trend.

Gauntlet: benchmark vs buy-&-hold, fee sensitivity, walk-forward,
permutation null (randomize sign), MC bootstrap.

Usage: python3 bin/phase11_tsmr.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATA_DIR = os.path.join(ROOT, "output", "hunt")
FEE = 0.00035
START = 30_000.0
N_NULL = 200
N_MC = 10_000
SEED = 29
TARGET_VOL_ANN = 0.20


def load_matrix():
    frames = {}
    for f in os.listdir(DATA_DIR):
        if not f.startswith("hl_") or not f.endswith("_1d.csv"):
            continue
        coin = f.split("_")[1]
        df = pd.read_csv(os.path.join(DATA_DIR, f))
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        frames[coin] = df.set_index("ts")["c"].rename(coin)
    m = pd.DataFrame(frames).sort_index()
    return m


def run_tsmr(m, coins, L=90, fee=FEE, start=START, vol_target=TARGET_VOL_ANN,
             signal_override=None):
    cols = [c for c in coins if c in m.columns]
    rets = m[cols].pct_change(fill_method=None)
    vol_d = rets.rolling(30).std()
    weight = (vol_target / np.sqrt(365)) / vol_d
    weight = weight.clip(upper=1.0)
    weight = weight.fillna(0.0)
    raw = rets * weight.shift(1)  # weights from prev close
    sign = signal_override if signal_override is not None else pd.DataFrame(
        np.where(m[cols].pct_change(L, fill_method=None) > 0, 1.0, 0.0),
        index=m.index, columns=cols)
    pnl = (raw * sign).sum(axis=1) / len(cols)  # equal allocation per coin
    # turnover cost: sign changes + weight changes
    chg = (sign.diff().abs().fillna(0) + weight.diff().abs().fillna(0)).sum(axis=1) / len(cols)
    costs = (chg * fee).sum()
    pnl = pnl - pd.Series(costs / len(m), index=m.index)
    return pnl, costs


def summarize(daily, start=START):
    eq = start * np.cumprod(1 + daily.to_numpy())
    net = eq[-1] / start - 1
    wins = daily[daily > 0]
    losses = daily[daily <= 0]
    pf = wins.sum() / -losses.sum() if losses.sum() < 0 else None
    full = np.concatenate([[start], eq])
    peak = np.maximum.accumulate(full)
    dd = ((full - peak) / peak).min()
    days = (daily.index[-1] - daily.index[0]).days
    return {"per_day_pct": round(net / days * 100, 4), "pf": round(pf, 2) if pf else None,
            "max_dd_pct": round(dd * 100, 2), "final_equity": round(eq[-1], 0),
            "net_pct": round(net * 100, 1)}


def main():
    m = load_matrix()
    m = m[m.index >= "2023-01-01"]
    coins = list(m.columns)
    out = {}
    print(f"matrix: {m.shape[0]} x {m.shape[1]}  ({m.index[0].date()} -> {m.index[-1].date()})")

    bh = m["BTC"].pct_change().dropna()
    s = summarize(bh)
    print(f"BTC buy&hold: %/day={s['per_day_pct']} DD={s['max_dd_pct']}% eq={s['final_equity']:.0f}")

    print("\n═══ 1) L-LOOKBACK SCREEN (all coins, vol-targeted, fees on) ═══")
    best = None
    for L in (30, 60, 90, 120, 180):
        pnl, costs = run_tsmr(m, coins, L=L)
        s = summarize(pnl)
        out[f"tsmr_L{L}"] = {**s}
        print(f"  L={L:>4}: %/day={s['per_day_pct']:>7} PF={s['pf']} DD={s['max_dd_pct']:>7}% eq={s['final_equity']:>8}")
        if best is None or s["per_day_pct"] > best[1]["per_day_pct"]:
            best = (L, s)
    L = best[0]
    pnl, costs = run_tsmr(m, coins, L=L)

    print("\n═══ 2) WALK-FORWARD ═══")
    wf = {}
    for a, b in [("2023-01-01", "2023-12-31"), ("2024-01-01", "2024-12-31"),
                 ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-08-23")]:
        seg = pnl[(pnl.index >= a) & (pnl.index < b)]
        s = summarize(seg)
        wf[f"{a}_{b}"] = s
        print(f"  {a} -> {b}: %/day={s['per_day_pct']:>7} PF={s['pf']} DD={s['max_dd_pct']}%")
    out["walkforward"] = wf

    print("\n═══ 3) PERMUTATION NULL (randomize trend sign per coin per week) ═══")
    rng = np.random.default_rng(SEED)
    null_pds = []
    weeks = m.index.to_period("W")
    rebal = pd.Series(m.index, index=weeks).groupby(level=0).max()
    for t in range(N_NULL):
        sig = pd.DataFrame(rng.integers(0, 2, size=(len(m), len(coins))).astype(float),
                           index=m.index, columns=coins)
        p, _ = run_tsmr(m, coins, L=L, signal_override=sig)
        s = summarize(p)
        null_pds.append(s["per_day_pct"])
    real = summarize(pnl)["per_day_pct"]
    null_pds = np.array(null_pds)
    out["null"] = {"n": N_NULL, "real": real,
                   "null_median": round(float(np.median(null_pds)), 4),
                   "null_p95": round(float(np.percentile(null_pds, 95)), 4),
                   "p_value": round(float((null_pds >= real).mean()), 4)}
    print(f"  real={real}; null med={out['null']['null_median']} p95={out['null']['null_p95']} p={out['null']['p_value']}")

    print("\n═══ 4) MC BOOTSTRAP ═══")
    weekly = (1 + pnl).resample("W-FRI").prod() - 1
    r = weekly.to_numpy()
    finals = np.empty(N_MC)
    dds = np.empty(N_MC)
    for i in range(N_MC):
        idx = rng.integers(0, len(r), size=len(r))
        eq = START * np.cumprod(1 + r[idx])
        full = np.concatenate([[START], eq])
        peak = np.maximum.accumulate(full)
        finals[i] = eq[-1]
        dds[i] = ((full - peak) / peak).min()
    out["mc"] = {"p_negative": round(float((finals < START).mean()), 4),
                 "median_equity": round(float(np.median(finals)), 0),
                 "p05_equity": round(float(np.percentile(finals, 5)), 0),
                 "dd_median": round(100 * float(np.median(dds)), 2),
                 "dd_p05": round(100 * float(np.percentile(dds, 5)), 2)}
    print(f"  p(neg)={out['mc']['p_negative']} med={out['mc']['median_equity']:.0f} "
          f"p05={out['mc']['p05_equity']:.0f} DD med={out['mc']['dd_median']}% p05={out['mc']['dd_p05']}%")

    out["best_L"] = L
    json.dump(out, open("output/hunt_tsmr.json", "w"), indent=1)
    print("\nsaved -> output/hunt_tsmr.json")


if __name__ == "__main__":
    main()
