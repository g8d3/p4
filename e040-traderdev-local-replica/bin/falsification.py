#!/usr/bin/env python3
"""Falsification battery for the EMA-VWAP micro-trail edge.

1. Permutation null: same trade frequency, random entry bars -> does
   random timing reproduce the returns? (p-value of the real strategy)
2. Time-shift null: real entries shifted +1/+2 bars.
3. Direction split: both / long / short.
4. Fee & slippage stress matrix.
5. Walk-forward: per-window net/day stability.

Usage: python3 bin/falsification.py
"""
import json
import math
import sys
import time

import numpy as np
import pandas as pd

from backtest import load, run

OUT = "output"
N_TRIALS = 120


def summary(df, window, ema=5, mult=0.02, commission=0.0005, funding=0.0,
            direction="both", slippage=0.0, long_sig_ov=None,
            short_sig_ov=None, vol_min=0.0, trend=0):
    d = df.copy()
    if window:
        a, b = window.split(":")
        d = d[(d["ts"] >= pd.Timestamp(a, tz="UTC")) &
              (d["ts"] < pd.Timestamp(b, tz="UTC"))].reset_index(drop=True)
    trades, eq, start, fund = run(d, ema_len=ema, atr_mult=mult,
                                  commission=commission, funding_hour=funding,
                                  direction=direction, slippage=slippage,
                                  long_sig_ov=long_sig_ov,
                                  short_sig_ov=short_sig_ov,
                                  vol_min_ratio=vol_min, trend_len=trend)
    days = max(1.0, (d["ts"].iloc[-1] - d["ts"].iloc[0]).total_seconds() / 86400)
    tdf = pd.DataFrame(trades)
    pf = None
    if len(tdf):
        gp = tdf[tdf.pnl_usd > 0].pnl_usd.sum()
        gl = -tdf[tdf.pnl_usd <= 0].pnl_usd.sum()
        pf = round(gp / gl, 3) if gl > 0 else None
    net = eq / start - 1
    per_day = (1 + net) ** (1 / days) - 1 if net > -1 else -1
    return {"trades": len(tdf), "net": round(net * 100, 2),
            "per_day_pct": round(per_day * 100, 4), "pf": pf}


def valid_bars(df):
    # emulate indicator warmup: bars where atr and vwap exist (>= ~120 bars in)
    return len(df) - 240


def permutations(df, window, n_trials=N_TRIALS, seed=42):
    d = df.copy()
    a, b = window.split(":")
    d = d[(d["ts"] >= pd.Timestamp(a, tz="UTC")) &
          (d["ts"] < pd.Timestamp(b, tz="UTC"))].reset_index(drop=True)
    n = len(d)
    rng = np.random.default_rng(seed)
    s0 = summary(df, window)
    # count real signals by direction (approx: trades count split)
    trades, *_ = run(d, ema_len=5, atr_mult=0.02)
    tdf = pd.DataFrame(trades)
    n_l = int((tdf.side == "L").sum())
    n_s = int((tdf.side == "S").sum())
    start_i = 60
    lo, hi = n_trials, 0
    results = []
    for _ in range(n_trials):
        li = np.sort(rng.integers(start_i, max(start_i + 1, n - 1), size=n_l + 1))
        si = np.sort(rng.integers(start_i, max(start_i + 1, n - 1), size=n_s + 1))
        larr = np.zeros(n, dtype=bool)
        sarr = np.zeros(n, dtype=bool)
        larr[li[:n_l]] = True
        sarr[si[:n_s]] = True
        r = summary(df, window, long_sig_ov=larr, short_sig_ov=sarr)
        results.append(r)
    res = pd.DataFrame(results)
    real = s0["per_day_pct"]
    pval = float((res["per_day_pct"] >= real).mean())
    return {
        "real": s0,
        "random_trials": n_trials,
        "random_net_p50": round(float(res["net"].median()), 2),
        "random_perday_p50": round(float(res["per_day_pct"].median()), 4),
        "random_pf_p50": round(float(res["pf"].median()), 3),
        "p_value_perday": round(pval, 4),
        "random_net_p95": round(float(res["net"].quantile(0.95)), 2),
    }


def shift_test(df, window, shift_bars):
    n = len(df)
    d = df.copy()
    a, b = window.split(":")
    d = d[(d["ts"] >= pd.Timestamp(a, tz="UTC")) &
          (d["ts"] < pd.Timestamp(b, tz="UTC"))].reset_index(drop=True)
    n = len(d)
    ema = d["c"].ewm(span=5, adjust=False).mean().to_numpy()
    day = d["ts"].dt.floor("D")
    pv = (d["c"] * d["v"]).groupby(day).cumsum().to_numpy()
    vv = d["v"].groupby(day).cumsum().to_numpy()
    vwap = np.where(vv > 0, pv / vv, np.nan)
    larr = np.zeros(n, dtype=bool)
    sarr = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if not (np.isnan(ema[i - 1]) or np.isnan(vwap[i - 1])):
            larr[i] = ema[i - 1] < vwap[i - 1] and ema[i] >= vwap[i]
            sarr[i] = ema[i - 1] > vwap[i - 1] and ema[i] <= vwap[i]
    out = {}
    for k in (0, 1, 2, 3):
        lk = np.roll(larr, k)
        sk = np.roll(sarr, k)
        out[k] = summary(df, window, long_sig_ov=lk, short_sig_ov=sk)
    return out


def main():
    df = load("output/btcusdt_2h.csv")
    win = "2024-08-01:2026-08-22"
    out = {}
    print("### 1. PERMUTATION NULL (Bybit BTC 2h, full window)", flush=True)
    out["permutation"] = permutations(df, win)
    print(json.dumps(out["permutation"], indent=1), flush=True)

    print("\n### 2. TIME-SHIFT NULL", flush=True)
    sh = shift_test(df, win, 0)
    out["shift"] = sh
    for k, v in sh.items():
        print(f"  shift+{k}: trades={v['trades']} per_day={v['per_day_pct']}% PF={v['pf']}", flush=True)

    print("\n### 3. DIRECTION SPLIT (Bybit BTC 2h)", flush=True)
    d = {"both": summary(df, win), "long": summary(df, win, direction="long"),
         "short": summary(df, win, direction="short")}
    out["direction_bybit"] = d
    for k, v in d.items():
        print(f"  {k:5} trades={v['trades']} per_day={v['per_day_pct']}% PF={v['pf']}", flush=True)

    print("\n### 3b. DIRECTION SPLIT (HL ETH 4h in-sample)", flush=True)
    hdf = load("output/hl_ETH_4h.csv")
    hwin = "2024-08-01:2026-04-30"
    d2 = {"both": summary(hdf, hwin, funding=0.000003125),
          "long": summary(hdf, hwin, funding=0.000003125, direction="long"),
          "short": summary(hdf, hwin, funding=0.000003125, direction="short")}
    out["direction_hl_eth"] = d2
    for k, v in d2.items():
        print(f"  {k:5} trades={v['trades']} per_day={v['per_day_pct']}% PF={v['pf']}", flush=True)

    print("\n### 4. FEE/SLIPPAGE STRESS (Bybit BTC 2h, long-only)", flush=True)
    stress = {}
    for comm in (0.0005, 0.001, 0.002):
        for slip in (0.0, 0.001, 0.003):
            key = f"comm{comm*100:.2f}%_slip{slip*100:.1f}%"
            stress[key] = summary(df, win, commission=comm, slippage=slip,
                                  direction="long")
            v = stress[key]
            print(f"  {key:22} per_day={v['per_day_pct']}% PF={v['pf']}", flush=True)
    out["stress"] = stress

    print("\n### 5. WALK-FORWARD (Bybit BTC 2h, 8 windows)", flush=True)
    wf_bybit = []
    starts = pd.date_range("2024-08-01", "2026-06-20", freq="90D")
    for s in starts:
        e = s + pd.Timedelta(days=90)
        if e > pd.Timestamp("2026-08-22", tz="UTC").tz_localize(None):
            continue
        w = f"{s.date()}:{(e + pd.Timedelta(days=1)).date()}"
        r = summary(df, w)
        wf_bybit.append({"window": w, **r})
        print(f"  {w} per_day={r['per_day_pct']}% PF={r['pf']}", flush=True)
    out["walkforward_bybit"] = wf_bybit

    print("\n### 5b. WALK-FORWARD (HL BTC 4h)", flush=True)
    wf_hl = []
    for s in starts[:6]:
        e = s + pd.Timedelta(days=90)
        w = f"{s.date()}:{(e + pd.Timedelta(days=1)).date()}"
        r = summary(hdf, w, funding=0.000002)
        wf_hl.append({"window": w, **r})
        print(f"  {w} per_day={r['per_day_pct']}% PF={r['pf']}", flush=True)
    out["walkforward_hl"] = wf_hl

    with open("output/falsification.json", "w") as f:
        json.dump(out, f, indent=1, default=str)
    print("\nsaved -> output/falsification.json")


if __name__ == "__main__":
    main()
