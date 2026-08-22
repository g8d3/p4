#!/usr/bin/env python3
"""Phase 2 — long-only + regime/trend filters matrix.

Questions:
- Does dropping the weak short leg raise PF and cut DD?
- Do volatility-regime (ATR% >= x * median) and trend (close vs EMA(n))
  filters help on the fresh OOS window?

Runs on HL 2h OOS (2026-05-01 -> 2026-08-22) and HL 4h in-sample
(2024-08-01 -> 2026-04-30) for BTC/ETH/SOL, and Bybit BTC 2h full.
"""
import json

import pandas as pd

from backtest import load, run

FUND = {"BTC": 0.000002, "ETH": 0.000003125, "SOL": 0.00000375}


def one(csv, window, coin, cfg, ema=5, mult=0.02):
    d = load(csv)
    if window:
        a, b = window.split(":")
        d = d[(d["ts"] >= pd.Timestamp(a, tz="UTC")) &
              (d["ts"] < pd.Timestamp(b, tz="UTC"))].reset_index(drop=True)
    trades, eq, start, fund = run(
        d, ema_len=ema, atr_mult=mult, commission=0.0005,
        funding_hour=FUND.get(coin, 0.0),
        direction=cfg.get("dir", "both"),
        vol_min_ratio=cfg.get("vol", 0.0), trend_len=cfg.get("trend", 0))
    days = max(1.0, (d["ts"].iloc[-1] - d["ts"].iloc[0]).total_seconds() / 86400)
    tdf = pd.DataFrame(trades)
    pf = None
    if len(tdf):
        gp = tdf[tdf.pnl_usd > 0].pnl_usd.sum()
        gl = -tdf[tdf.pnl_usd <= 0].pnl_usd.sum()
        pf = round(gp / gl, 2) if gl > 0 else None
    net = eq / start - 1
    per_day = round((((1 + net) ** (1 / days) - 1) * 100), 4)
    eq_cum = start + tdf.pnl_usd.cumsum()
    dd = round(100 * float(((eq_cum - eq_cum.cummax()) / eq_cum.cummax()).min()), 2)
    return {"trades": len(tdf), "per_day": per_day, "pf": pf, "dd": dd, "net": round(net * 100, 1)}


CFGS = {
    "both":            {},
    "long":            {"dir": "long"},
    "long+trend100":   {"dir": "long", "trend": 100},
    "long+vol090":     {"dir": "long", "vol": 0.9},
    "long+tr+vol":     {"dir": "long", "trend": 100, "vol": 0.9},
    "short":           {"dir": "short"},
    "long+trend200":   {"dir": "long", "trend": 200},
}


def main():
    out = {}
    datasets = [
        ("OOS 2h HL", "output/hl_BTC_2h.csv", "2026-05-01:2026-08-22", "BTC"),
        ("OOS 2h HL", "output/hl_ETH_2h.csv", "2026-05-01:2026-08-22", "ETH"),
        ("OOS 2h HL", "output/hl_SOL_2h.csv", "2026-05-01:2026-08-22", "SOL"),
        ("IN 4h HL", "output/hl_BTC_4h.csv", "2024-08-01:2026-04-30", "BTC"),
        ("IN 4h HL", "output/hl_ETH_4h.csv", "2024-08-01:2026-04-30", "ETH"),
        ("IN 4h HL", "output/hl_SOL_4h.csv", "2024-08-01:2026-04-30", "SOL"),
        ("FULL Bybit", "output/btcusdt_2h.csv", "2024-08-01:2026-08-22", "BTC"),
    ]
    for label, csv, win, coin in datasets:
        print(f"\n═══ {label} {coin} ═══")
        for name, cfg in CFGS.items():
            r = one(csv, win, coin, cfg)
            out[f"{label}|{coin}|{name}"] = r
            print(f"  {name:15} tr={r['trades']:>4}  %/day={r['per_day']:>7}  "
                  f"PF={r['pf']!s:>6}  DD%={r['dd']:>6}  net%={r['net']:>10}")
    json.dump(out, open("output/phase2_filters.json", "w"), indent=1)
    print("\nsaved -> output/phase2_filters.json")


if __name__ == "__main__":
    main()
