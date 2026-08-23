#!/usr/bin/env python3
"""Build the interactive HTML report for e040 (mobile-first, self-contained).

Reads output/*.json + recomputes MC histograms for the winner config
(EMA7/0.02, 1d, intrabar) and writes <exp>/REPORT.html.
Run: python3 bin/build_report_html.py
"""
import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

OUT = os.path.join(ROOT, "output")


def load_jsons():
    out = {}
    for name in ("phase7.json", "phase7_intrabar.json", "mc_1d.json",
                 "falsification.json", "metrics_final.json",
                 "synthetic_null.json", "hunt_tsmr.json"):
        p = os.path.join(OUT, name)
        if os.path.exists(p):
            out[name] = json.load(open(p))
    return out


def mc_hist(returns, n=10_000, seed=7, start=10_000.0):
    rng = np.random.default_rng(seed)
    r = np.asarray(returns, dtype=float)
    n_t = len(r)
    finals = np.empty(n)
    dds = np.empty(n)
    for i in range(n):
        idx = rng.integers(0, n_t, size=n_t)
        eq = start * np.cumprod(1 + r[idx])
        full = np.concatenate([[start], eq])
        peak = np.maximum.accumulate(full)
        finals[i] = eq[-1]
        dds[i] = ((full - peak) / peak).min()
    bins, edges = np.histogram(finals, bins=40)
    return {"bins": bins.tolist(), "edges": edges.tolist(),
            "p_neg": float((finals < start).mean()),
            "median": float(np.median(finals)),
            "p05": float(np.percentile(finals, 5)),
            "dd_med": float(np.median(dds)), "dd_p05": float(np.percentile(dds, 5))}


def main():
    data = load_jsons()

    # recompute returns for winner configs (ema7, BTC+ETH+SOL) for histograms
    spec = importlib.util.spec_from_file_location("p5mod", os.path.join(ROOT, "bin", "phase5_daily_weekly.py"))
    p5 = importlib.util.module_from_spec(spec)
    sys.modules["p5mod"] = p5
    spec.loader.exec_module(p5)
    from bin.backtest import load
    mc = {}
    for coin in ("BTC", "ETH", "SOL"):
        h1d = load(f"output/{coin.lower()}usdt_1d_full.csv")
        m5 = load(f"output/{coin.lower()}usdt_5m.csv")
        m5 = m5[(m5["ts"] >= pd.Timestamp("2024-08-01", tz="UTC")) &
                (m5["ts"] < pd.Timestamp("2026-08-22", tz="UTC"))].reset_index(drop=True)
        r = p5.intrabar_daily(h1d, m5, mult=0.02, ema_len=7)
        rets = [float(x) for x in r.pop("returns_", [])]
        mc[f"{coin}_ema7"] = mc_hist(rets)
        print(f"MC {coin} ema7: {mc[f'{coin}_ema7']}")
    data["mc_histograms"] = mc

    # --- demo chart: pick the best BTC EMA7 trade, embed the window ---
    h1d = load("output/btcusdt_1d_full.csv")
    m5b = load("output/btcusdt_5m.csv")
    m5b = m5b[(m5b["ts"] >= pd.Timestamp("2024-08-01", tz="UTC")) &
              (m5b["ts"] < pd.Timestamp("2026-08-22", tz="UTC"))].reset_index(drop=True)
    rb = p5.intrabar_daily(h1d, m5b, mult=0.02, ema_len=7)
    tlist = rb.pop("trades_", [])
    rb.pop("returns_", None)
    data["btc_ema7_trades"] = tlist
    if tlist:
        demo = max(tlist, key=lambda t: t["pnl_usd"])
        i0 = int(np.flatnonzero(
            ((h1d["ts"] - pd.Timestamp(demo["entry_day"], tz="UTC")).dt.total_seconds().abs()) < 86400)[0])
        i1 = int(np.flatnonzero(
            ((h1d["ts"] - pd.Timestamp(demo["exit_day"], tz="UTC")).dt.total_seconds().abs()) < 86400)[0])
        a, b = max(0, i0 - 3), min(len(h1d), i1 + 3)
        sind = p5.indicators(h1d.copy(), ema_len=7)
        win = sind.iloc[a:b]
        data["demo"] = {
            "trade": demo,
            "dates": [str(x.date()) for x in win["ts"]],
            "close": [round(float(x), 2) for x in win["c"]],
            "volume": [float(x) for x in win["v"]],
            "atr": [round(float(x), 2) for x in win["atr"]],
            "entry_idx": i0 - a, "exit_idx": i1 - a,
            "mult": 0.02,
        }
        print("demo trade:", demo)


    html_template = open(os.path.join(ROOT, "bin", "report_template.html")).read()
    chartjs = open(os.path.join(ROOT, "bin", "vendor", "chart.umd.min.js")).read()
    html = html_template.replace("__DATA__", json.dumps(data)) \
                        .replace("/*__CHARTJS__*/", chartjs)
    path = os.path.join(ROOT, "REPORT.html")
    with open(path, "w") as f:
        f.write(html)
    print(f"wrote {path} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
