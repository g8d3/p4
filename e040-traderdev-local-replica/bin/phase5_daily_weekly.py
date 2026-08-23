#!/usr/bin/env python3
"""Phase 5 — bigger timeframe version (1d / 1w).

Hypothesis: at bigger TFs the captured % move per trade is larger, so the
same fixed costs become a smaller share — but the intrabar fill optimism
grows. Test BOTH levels: bar-level (optimistic) and intrabar-5m for 1d.

VWAP anchor: weekly (a daily-anchored VWAP on daily bars is degenerate —
each bar IS one day). On 1w bars weekly VWAP is degenerate too (VWAP == close)
— reported as 'degenerate' and interpreted as ema-vs-close cross instead.

Usage: python3 bin/phase5_daily_weekly.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bin.backtest import load, run

OUT = "output"


def indicators(df, ema_len=5, atr_len=14, vwap_mode="weekly"):
    d = df.copy()
    d["ema"] = d["c"].ewm(span=ema_len, adjust=False).mean()
    d["tr"] = np.maximum(
        d["h"] - d["l"],
        np.maximum((d["h"] - d["c"].shift()).abs(),
                   (d["l"] - d["c"].shift()).abs()))
    d["atr"] = d["tr"].ewm(alpha=1 / atr_len, adjust=False).mean()
    if vwap_mode == "weekly":
        wk = d["ts"].dt.to_period("W").dt.to_timestamp()
        pv = (d["c"] * d["v"]).groupby(wk).cumsum()
        vv = d["v"].groupby(wk).cumsum()
        d["vwap"] = np.where(vv > 0, pv / vv, np.nan)
        d["vwap_degen"] = False
    elif vwap_mode == "degenerate":  # same-bar vwap == close (1w case)
        d["vwap"] = d["c"]
        d["vwap_degen"] = True
    return d


def bar_level(df, window, mult=0.02, vwap_mode="weekly", ema=5):
    d = df.copy()
    if window:
        a, b = window.split(":")
        d = d[(d["ts"] >= pd.Timestamp(a, tz="UTC")) &
              (d["ts"] < pd.Timestamp(b, tz="UTC"))].reset_index(drop=True)
    trades, eq, start, _ = run(d, ema_len=ema, atr_mult=mult,
                               commission=0.0005, vwap_mode=vwap_mode)
    days = max(1.0, (d["ts"].iloc[-1] - d["ts"].iloc[0]).total_seconds() / 86400)
    tdf = pd.DataFrame(trades)
    gp = tdf[tdf.pnl_usd > 0].pnl_usd.sum()
    gl = -tdf[tdf.pnl_usd <= 0].pnl_usd.sum()
    pf = round(gp / gl, 2) if gl > 0 else None
    net = eq / start - 1
    eqc = start + tdf.pnl_usd.cumsum()
    dd = round(100 * float(((eqc - eqc.cummax()) / eqc.cummax()).min()), 2)
    d = {"trades": len(tdf), "per_day": round(((1 + net) ** (1 / days) - 1) * 100, 4),
         "pf": pf, "dd": dd, "net_pct": round(net * 100, 1), "days": round(days, 1)}
    if tdf.empty:
        d["returns_"] = []
        d["trades_"] = []
    else:
        d["returns_"] = rets
        d["trades_"] = [{"side": r.side, "entry_day": r.entry_day, "exit_day": r.exit_day,
                         "entry_px": r.entry_px, "exit_px": r.exit_px,
                         "pnl_usd": r.pnl_usd, "equity": r.equity} for r in tdf.itertuples()]
    return d


def intrabar_daily(h1d, m5, mult=0.02, commission=0.0005, start_cap=10_000.0,
                  ema_len=5):
    """1d signals/ATR, fills on 5m path inside each daily bucket."""
    h1d = indicators(h1d.copy(), ema_len=ema_len)
    h1d["bucket"] = h1d["ts"].dt.floor("D")
    h1d["bar"] = range(len(h1d))
    m5 = m5.copy()
    m5["bucket"] = m5["ts"].dt.floor("D")
    merged = m5.merge(h1d[["bucket", "ema", "vwap", "atr", "c", "bar"]],
                      on="bucket", how="left", suffixes=("", "_1d"))

    equity = start_cap
    trades = []
    pos = 0
    stop = np.inf
    armed = False
    entry_price = np.nan
    entry_day = None
    entry_bar = -1
    for bar_id, grp in merged.groupby("bar", dropna=True):
        if np.isnan(grp["atr"].iloc[0]):
            continue
        ema_i = grp["ema"].iloc[0]
        vwap_i = grp["vwap"].iloc[0]
        T = grp["atr"].iloc[0] * mult
        if bar_id == 0:
            prev_ema, prev_vwap = np.nan, np.nan
        else:
            prev_ema = h1d.iloc[bar_id - 1]["ema"]
            prev_vwap = h1d.iloc[bar_id - 1]["vwap"]
        long_sig = short_sig = False
        if pos == 0 and not np.isnan(prev_ema) and not np.isnan(prev_vwap):
            long_sig = prev_ema < prev_vwap and ema_i >= vwap_i
            short_sig = prev_ema > prev_vwap and ema_i <= vwap_i
        if pos == 0 and long_sig:
            pos = 1; entry_price = grp["c_1d"].iloc[0]
            entry_day = str(h1d.iloc[bar_id]["ts"].date())
            entry_bar = bar_id
            armed = False; stop = np.inf
        elif pos == 0 and short_sig:
            pos = -1; entry_price = grp["c_1d"].iloc[0]
            entry_day = str(h1d.iloc[bar_id]["ts"].date())
            entry_bar = bar_id
            armed = False; stop = np.inf
        exit_px = None
        if pos != 0 and bar_id <= entry_bar:
            pos_walk = False
        else:
            pos_walk = True
        for row in grp.itertuples():
            if pos == 0 or not pos_walk:
                break
            h_, l_, o_, c_ = row.h, row.l, row.o, row.c
            wasA = armed
            if pos == 1:
                if not armed and h_ >= entry_price + T:
                    armed = True; stop = h_ - T
                elif armed:
                    stop = max(stop, h_ - T)
                if armed and l_ <= stop:
                    exit_px = (o_ if (wasA and o_ < stop) else stop)
                    break
            else:
                if not armed and l_ <= entry_price - T:
                    armed = True; stop = l_ + T
                elif armed:
                    stop = min(stop, l_ + T)
                if armed and h_ >= stop:
                    exit_px = (o_ if (wasA and o_ > stop) else stop)
                    break
        if exit_px is not None:
            notional = equity
            pnl = notional * (exit_px - entry_price) / entry_price * pos - 2 * commission * notional
            equity += pnl
            trades.append({"bar": bar_id, "side": "L" if pos == 1 else "S",
                           "pnl_usd": round(pnl, 2), "equity": round(equity, 2),
                           "entry_day": entry_day, "exit_day": str(h1d.iloc[bar_id]["ts"].date()),
                           "entry_px": round(entry_price, 2), "exit_px": round(exit_px, 2)})
            pos = 0
        if pos != 0:
            c_1d = grp["c_1d"].iloc[0]
            rev = (pos == 1 and prev_ema > prev_vwap and ema_i <= vwap_i) or \
                  (pos == -1 and prev_ema < prev_vwap and ema_i >= vwap_i)
            if rev:
                notional = equity
                pnl = notional * (c_1d - entry_price) / entry_price * pos - 2 * commission * notional
                equity += pnl
                trades.append({"bar": bar_id, "side": "L" if pos == 1 else "S",
                               "pnl_usd": round(pnl, 2), "equity": round(equity, 2),
                               "entry_day": entry_day, "exit_day": str(h1d.iloc[bar_id]["ts"].date()),
                               "entry_px": round(entry_price, 2), "exit_px": round(c_1d, 2)})
                pos = 0
    if pos != 0:
        notional = equity
        c_last = h1d["c"].iloc[-1]
        pnl = notional * (c_last - entry_price) / entry_price * pos - 2 * commission * notional
        equity += pnl
        trades.append({"bar": len(h1d) - 1, "side": "L" if pos == 1 else "S",
                       "pnl_usd": round(pnl, 2), "equity": round(equity, 2),
                       "entry_day": entry_day, "exit_day": str(h1d.iloc[-1]["ts"].date()),
                       "entry_px": round(entry_price, 2), "exit_px": round(c_last, 2)})
    tdf = pd.DataFrame(trades)
    rets = []
    for row in tdf.itertuples():
        prev_eq = row.equity - row.pnl_usd
        rets.append(row.pnl_usd / prev_eq if prev_eq > 0 else 0.0)
    days = max(1.0, (m5["ts"].iloc[-1] - m5["ts"].iloc[0]).total_seconds() / 86400)
    gp = tdf[tdf.pnl_usd > 0].pnl_usd.sum()
    gl = -tdf[tdf.pnl_usd <= 0].pnl_usd.sum()
    pf = round(gp / gl, 2) if gl > 0 else None
    net = equity / start_cap - 1
    eqc = start_cap + tdf.pnl_usd.cumsum()
    dd = round(100 * float(((eqc - eqc.cummax()) / eqc.cummax()).min()), 2)
    d = {"trades": len(tdf), "per_day": round(((1 + net) ** (1 / days) - 1) * 100, 4),
         "pf": pf, "dd": dd, "net_pct": round(net * 100, 1), "days": round(days, 1)}
    if tdf.empty:
        d["returns_"] = []
        d["trades_"] = []
    else:
        d["returns_"] = rets
        d["trades_"] = [{"side": r.side, "entry_day": r.entry_day, "exit_day": r.exit_day,
                         "entry_px": r.entry_px, "exit_px": r.exit_px,
                         "pnl_usd": r.pnl_usd, "equity": r.equity} for r in tdf.itertuples()]
    return d


def hl_1d(coins=("BTC", "ETH", "SOL")):
    raw = pd.read_csv(os.path.join(ROOT, "..", "e025-hyperliquid-candle-tails",
                                   "ag-01-data", "output", "candles_raw.csv"),
                      usecols=["coin", "tf", "t_ms", "o", "h", "l", "c", "v"])
    raw = raw[(raw["tf"] == "1d") & (raw["coin"].isin(coins))].copy()
    raw["ts"] = pd.to_datetime(raw["t_ms"], unit="ms", utc=True)
    raw = raw.rename(columns={"o": "o", "h": "h", "l": "l", "c": "c", "v": "v"})
    out = {}
    for coin, grp in raw.groupby("coin"):
        out[coin] = grp[["ts", "o", "h", "l", "c", "v"]].sort_values("ts").reset_index(drop=True)
    return out


WIN = "2024-08-01:2026-08-22"
WIN_HL = "2024-08-01:2026-08-13"


def main():
    res = {}
    print("═══ 1d bar-level (optimistic fills), weekly-anchored VWAP ═══")
    for label, df in [("Bybit BTC", load("output/btcusdt_1d.csv")),
                      ("Bybit ETH", load("output/ethusdt_1d.csv"))]:
        for mult in (0.02, 0.05):
            r = bar_level(df, WIN, mult=mult)
            res[f"{label} 1d bar mult{mult}"] = r
            print(f"  {label:12} mult={mult:.2f}: {r}")
    hld = hl_1d()
    for coin, df in hld.items():
        r = bar_level(df, WIN_HL, mult=0.02)
        res[f"HL {coin} 1d bar mult0.02"] = r
        print(f"  HL {coin:9} mult=0.02: {r}")

    print("\n═══ 1d INTRABAR (realistic 5m fills) — Bybit BTC only ═══")
    m5 = load("output/btcusdt_5m.csv")
    m5 = m5[(m5["ts"] >= pd.Timestamp("2024-08-01", tz="UTC")) &
            (m5["ts"] < pd.Timestamp("2026-08-22", tz="UTC"))].reset_index(drop=True)
    h1d = load("output/btcusdt_1d.csv")
    for mult in (0.02, 0.05):
        r = intrabar_daily(h1d, m5, mult=mult)
        res[f"1d INTRABAR mult{mult}"] = r
        print(f"  1d intrabar mult={mult:.2f}: {r}")

    print("\n═══ 1w bar-level (degenerate vwap -> ema-vs-close cross) ═══")
    dfw = load("output/btcusdt_1w.csv")
    for mult in (0.05, 0.1):
        r = bar_level(dfw, WIN, mult=mult, vwap_mode="degenerate")
        res[f"Bybit BTC 1w bar deg mult{mult}"] = r
        print(f"  BTC 1w mult={mult:.2f}: {r}")
    json.dump(res, open("output/phase5.json", "w"), indent=1)
    print("\nsaved -> output/phase5.json")


if __name__ == "__main__":
    main()
