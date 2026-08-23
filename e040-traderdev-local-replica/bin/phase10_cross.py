#!/usr/bin/env python3
"""Phase 10 — cross-sectional momentum screen (the "hunt").

Weekly rebalance: rank the HL perp universe by L-day momentum, long top-K,
short bottom-K, equal weight, dollar-neutral, 1x. Costs modeled per rebalance.
Through the same gauntlet: walk-forward, permutation null (shuffle ranks),
Monte Carlo bootstrap of weekly returns, fee sensitivity.

Usage: python3 bin/phase10_cross.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATA_DIR = os.path.join(ROOT, "output", "hunt")
COINS = ["BTC", "ETH", "SOL", "HYPE", "PUMP", "ZEC", "XRP", "LIT", "DOGE",
         "CRV", "AAVE", "XMR"]
FEE = 0.00035          # taker per side
START = 30_000.0
N_NULL = 200
N_MC = 10_000
SEED = 17


def load_matrix():
    frames = {}
    for c in COINS:
        p = os.path.join(DATA_DIR, f"hl_{c}_1d.csv")
        if not os.path.exists(p):
            continue
        df = pd.read_csv(p)
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        df = df.set_index("ts")["c"].rename(c)
        frames[c] = df
    m = pd.DataFrame(frames).sort_index()
    return m


def momentum_matrix(m, L):
    return m.pct_change(L, fill_method=None)


def run_strategy(m, L=42, K=3, fee=FEE, rebalance="W-FRI", start=START):
    mom = momentum_matrix(m, L)
    # rebalance dates: last trading day of each week
    weeks = m.index.to_period("W")
    rebal_days = pd.Series(m.index, index=weeks).groupby(level=0).max()
    # daily portfolio returns: hold from close of rebal day to next
    pnl = pd.Series(0.0, index=m.index)
    costs = 0.0
    prev_w = pd.Series(0.0, index=m.columns)
    dates = list(rebal_days)
    for i in range(len(dates) - 1):
        d0 = dates[i]
        d1 = dates[i + 1]
        row = mom.loc[d0].dropna()
        if len(row) < 6:
            continue
        ranked = row.sort_values(ascending=False)
        long_coins = list(ranked.head(K).index)
        short_coins = list(ranked.tail(K).index)
        w = pd.Series(0.0, index=m.columns)
        w[long_coins] = 1.0 / K
        w[short_coins] = -1.0 / K
        # costs: turnover in weights
        turnover = float((w - prev_w).abs().sum()) / 2.0
        costs += turnover * fee * 2.0  # each leg change = close+open at taker
        prev_w = w
        # daily returns over the holding window
        seg = m.loc[d0:d1].pct_change(fill_method=None).iloc[1:]
        if seg.empty:
            continue
        for d, rets in seg.iterrows():
            pnl.loc[d] += float((w * rets).sum())
    daily = pnl - daily_cost_share(costs, len(pnl))
    return daily, costs


def daily_cost_share(costs, n):
    return costs / n


def summarize(daily, start=START, label=""):
    eq = start * np.cumprod(1 + daily.to_numpy())
    days = (daily.index[-1] - daily.index[0]).days
    net = eq[-1] / start - 1
    wins = daily[daily > 0]
    losses = daily[daily <= 0]
    pf = wins.sum() / -losses.sum() if len(losses) and losses.sum() < 0 else None
    peak = np.maximum.accumulate(np.concatenate([[start], eq]))
    dd = ((np.concatenate([[start], eq]) - peak) / peak).min()
    weekly = (1 + daily).resample("W-FRI").prod() - 1
    ann = (1 + weekly).prod() ** (52 / len(weekly)) - 1
    return {"label": label, "days": days, "per_day_pct": round((net / days) * 100, 4),
            "cagr_pct": round(ann * 100, 1), "pf": round(pf, 2) if pf else None,
            "max_dd_pct": round(dd * 100, 2), "final_equity": round(eq[-1], 0)}


def main():
    m = load_matrix()
    m = m[m.index >= "2023-01-01"]
    out = {}
    print(f"matrix: {m.shape[0]} days x {m.shape[1]} coins  ({m.index[0].date()} -> {m.index[-1].date()})")

    print("\n═══ 1) LOOKBACK x K SCREEN (fees on) ═══")
    for L in (21, 42, 63, 126):
        for K in (3, 4):
            daily, costs = run_strategy(m, L=L, K=K)
            s = summarize(daily, label=f"L{L}_K{K}")
            out[f"screen_L{L}_K{K}"] = {**s, "total_fees_pct": round(costs / START * 100, 2)}
            print(f"  L={L:>4} K={K}: %/day={s['per_day_pct']:>7} cagr={s['cagr_pct']:>8}% "
                  f"PF={s['pf']} DD={s['max_dd_pct']:>7}% eq={s['final_equity']:>9.0f}")

    print("\n═══ 2) WALK-FORWARD (best-of-screen, 4 windows) ═══")
    L, K = 42, 3
    daily, _ = run_strategy(m, L=L, K=K)
    wf = {}
    for i, (a, b) in enumerate([("2023-01-01", "2023-12-31"), ("2024-01-01", "2024-12-31"),
                                ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-08-23")]):
        seg = daily[(daily.index >= a) & (daily.index < b)]
        if not len(seg):
            continue
        s = summarize(seg, label=f"{a}_{b}")
        wf[f"{a}_{b}"] = s
        print(f"  {a} -> {b}: %/day={s['per_day_pct']:>7} PF={s['pf']} DD={s['max_dd_pct']}%")
    out["walkforward"] = wf

    print("\n═══ 3) PERMUTATION NULL (shuffle coin ranks each rebalance) ═══")
    rng = np.random.default_rng(SEED)
    null_pds = []
    for t in range(N_NULL):
        steps = max(1, int(len(m) / 120))
        perms = [rng.permutation(m.columns) for _ in range(steps * 3)]
        mm = momentum_matrix(m, L)
        pi = 0
        pnl = pd.Series(0.0, index=m.index)
        weeks = m.index.to_period("W")
        rebal_days = pd.Series(m.index, index=weeks).groupby(level=0).max()
        dates = list(rebal_days)
        for i in range(len(dates) - 1):
            d0, d1 = dates[i], dates[i + 1]
            perm = perms[pi % len(perms)]
            pi += 1
            row = mm.loc[d0].dropna()
            cols = [c for c in perm if c in row.index]
            if len(cols) < 6:
                continue
            s = row[cols].sort_values(ascending=False)
            long_c = list(s.head(K).index)
            short_c = list(s.tail(K).index)
            w = pd.Series(0.0, index=m.columns)
            w[long_c] = 1.0 / K
            w[short_c] = -1.0 / K
            seg = m.loc[d0:d1].pct_change(fill_method=None).iloc[1:]
            for d, rets in seg.iterrows():
                pnl.loc[d] += float((w * rets).sum())
        s = summarize(pnl, label="null")
        null_pds.append(s["per_day_pct"])
    real = summarize(daily, label="real")["per_day_pct"]
    null_pds = np.array(null_pds)
    out["null"] = {"n": N_NULL, "real_per_day": real,
                   "null_median": round(float(np.median(null_pds)), 4),
                   "null_p95": round(float(np.percentile(null_pds, 95)), 4),
                   "p_value": round(float((null_pds >= real).mean()), 4)}
    print(f"  real %/day={real}; null median={out['null']['null_median']} p95={out['null']['null_p95']} p={out['null']['p_value']}")

    print("\n═══ 4) MC BOOTSTRAP (weekly returns reshuffle) ═══")
    weekly = (1 + daily).resample("W-FRI").prod() - 1
    r = weekly.to_numpy()
    rng = np.random.default_rng(SEED)
    finals = np.empty(N_MC)
    dds = np.empty(N_MC)
    for i in range(N_MC):
        idx = rng.integers(0, len(r), size=len(r))
        eq = START * np.cumprod(1 + r[idx])
        full = np.concatenate([[START], eq])
        peak = np.maximum.accumulate(full)
        finals[i] = eq[-1]
        dds[i] = ((full - peak) / peak).min()
    mcres = {"p_negative": round(float((finals < START).mean()), 4),
             "median_equity": round(float(np.median(finals)), 0),
             "p05_equity": round(float(np.percentile(finals, 5)), 0),
             "dd_median": round(100 * float(np.median(dds)), 2),
             "dd_p05": round(100 * float(np.percentile(dds, 5)), 2)}
    out["mc"] = mcres
    print(f"  p(neg)={mcres['p_negative']} med_eq={mcres['median_equity']:.0f} p05_eq={mcres['p05_equity']:.0f} DD med={mcres['dd_median']}% p05={mcres['dd_p05']}%")

    json.dump(out, open("output/hunt_cross.json", "w"), indent=1)
    print("\nsaved -> output/hunt_cross.json")


if __name__ == "__main__":
    main()
