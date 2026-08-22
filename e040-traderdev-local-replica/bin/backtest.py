#!/usr/bin/env python3
"""Local replica of the TraderDev leaderboard pattern:
EMA(N) x VWAP(daily-anchored, close source) cross + ATR trailing stop.

Engine semantics (from TraderDev codegen rules + TradingView trail order):
- signals on bar close, entries at bar close (process_orders_on_close)
- opposite cross REVERSES at bar close (TV auto-reversal)
- exit order placed EVERY bar: trail_points = trail_offset = atr*mult
  (re-issued with current ATR). Trail has NO floor stop before arming:
  arm when price first moves T in favor, stop = best - T afterwards,
  ratchet only (never loosens), evaluated from the bar AFTER placement.
- sizing: notional = 10 x equity, commission 0.05% per side, no slippage

Usage: python3 bin/backtest.py --csv <in.csv> --ema 5 --mult 0.02
       [--window 2024-08-01:2026-04-30] [--tag ema5_atr002] [--trail high]
"""
import argparse
import json
import math
import os

import numpy as np
import pandas as pd


def load(csv_path):
    df = pd.read_csv(csv_path)
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.sort_values("ts").reset_index(drop=True)


def add_indicators(df, ema_len, atr_len, vwap_mode):
    df["ema"] = df["c"].ewm(span=ema_len, adjust=False).mean()
    df["tr"] = np.maximum(
        df["h"] - df["l"],
        np.maximum((df["h"] - df["c"].shift()).abs(),
                   (df["l"] - df["c"].shift()).abs()))
    df["atr"] = df["tr"].ewm(alpha=1 / atr_len, adjust=False).mean()
    if vwap_mode == "daily":
        day = df["ts"].dt.floor("D")
        pv = (df["c"] * df["v"]).groupby(day).cumsum()
        vv = df["v"].groupby(day).cumsum()
        df["vwap"] = np.where(vv > 0, pv / vv, np.nan)
    elif vwap_mode == "weekly":
        wk = df["ts"].dt.to_period("W").dt.to_timestamp()
        pv = (df["c"] * df["v"]).groupby(wk).cumsum()
        vv = df["v"].groupby(wk).cumsum()
        df["vwap"] = np.where(vv > 0, pv / vv, np.nan)
    elif vwap_mode == "degenerate":
        df["vwap"] = df["c"]
    elif vwap_mode == "rolling_100":
        pv = (df["c"] * df["v"]).rolling(100).sum()
        vv = df["v"].rolling(100).sum()
        df["vwap"] = np.where(vv > 0, pv / vv, np.nan)
    else:
        raise ValueError(vwap_mode)
    return df


def close_position(trades, equity, times, entry_i, i, times_enter, times_exit,
                   side, entry_price, fill, pos, commission, leverage,
                   slippage=0.0):
    notional = leverage * equity
    pnl_usd = notional * (fill - entry_price) / entry_price * pos
    pnl_usd -= (2 * commission + 2 * slippage) * notional
    equity += pnl_usd
    trades.append({
        "entry_i": entry_i, "exit_i": i,
        "entry_dt": str(times[entry_i]), "exit_dt": str(times[i]),
        "side": side, "entry_px": round(entry_price, 4),
        "exit_px": round(fill, 4), "pnl_usd": round(pnl_usd, 2),
        "equity": round(equity, 2), "bars": i - entry_i,
    })
    return equity


def run(df, ema_len, atr_mult, vwap_mode="daily", atr_len=14,
        commission=0.0005, leverage=1, start_capital=10_000.0,
        trail="high", double_exit=False, funding_hour=0.0,
        direction="both", slippage=0.0,
        long_sig_ov=None, short_sig_ov=None,
        vol_min_ratio=0.0, trend_len=0):
    df = df.copy()
    df = add_indicators(df, ema_len, atr_len, vwap_mode)
    n = len(df)

    equity = start_capital
    trades = []
    pos = 0
    stop = math.inf
    armed = False
    best = math.nan
    m_armed = False
    m_stop = math.inf
    entry_price = math.nan
    entry_i = -1

    closes = df["c"].to_numpy()
    highs = df["h"].to_numpy()
    lows = df["l"].to_numpy()
    opens = df["o"].to_numpy()
    atrs = df["atr"].to_numpy()
    emas = df["ema"].to_numpy()
    vwaps = df["vwap"].to_numpy()
    times = df["ts"].to_numpy()
    freq_ms = int(pd.Timedelta(df["ts"].diff().dropna().min()).total_seconds() * 1000)
    if trend_len > 0:
        df["ema_trend"] = df["c"].ewm(span=trend_len, adjust=False).mean()
    if vol_min_ratio > 0:
        df["atr_pct"] = df["atr"] / df["c"]
        vol_win = max(100, int(675.0 / (freq_ms / 7_200_000)))
        df["vol_med"] = df["atr_pct"].rolling(vol_win, min_periods=120).median()
    ema_trends = df["ema_trend"].to_numpy() if trend_len > 0 else None
    atr_pcts = df["atr_pct"].to_numpy() if vol_min_ratio > 0 else None
    vol_meds = df["vol_med"].to_numpy() if vol_min_ratio > 0 else None
    funding_paid = 0.0

    for i in range(n):
        c, h, lo, op = closes[i], highs[i], lows[i], opens[i]
        atr_i = atrs[i]
        ema_i, vwap_i = emas[i], vwaps[i]
        if math.isnan(atr_i) or math.isnan(vwap_i):
            continue
        T = atr_i * atr_mult
        entered_this_bar = pos == 0 and False
        # --- 1. trail eval for positions opened on EARLIER bars ---
        fill = None
        was_armed = armed
        if pos == 1 and i > entry_i and not armed and h >= entry_price + T:
            armed = True
            best = h
            stop = best - T
        if pos == -1 and i > entry_i and not armed and lo <= entry_price - T:
            armed = True
            best = lo
            stop = best + T
        if pos == 1 and armed and lo <= stop:
            fill = op if (was_armed and op < stop) else stop
        elif pos == -1 and armed and h >= stop:
            fill = op if (was_armed and op > stop) else stop
        # --- 1b. mirror exit: the OTHER side's trail order applied to this
        # position (their engine fires BOTH strategy.exit orders every bar).
        # Conservative: when both trip the same bar, take the WORSE fill.
        mirror_fill = None
        if double_exit and pos == 1:
            if not m_armed and lo <= entry_price - T:
                m_armed = True
                m_stop = lo + T
            elif m_armed:
                m_stop = min(m_stop, lo + T)
            if m_armed and h >= m_stop:
                mirror_fill = op if op < m_stop else m_stop
        elif double_exit and pos == -1:
            if not m_armed and h >= entry_price + T:
                m_armed = True
                m_stop = h - T
            elif m_armed:
                m_stop = max(m_stop, h - T)
            if m_armed and lo <= m_stop:
                mirror_fill = op if op > m_stop else m_stop
        if mirror_fill is not None and double_exit:
            if pos == 1:
                fill = min(fill, mirror_fill) if fill is not None else mirror_fill
            else:
                fill = max(fill, mirror_fill) if fill is not None else mirror_fill
        if fill is not None:
            equity = close_position(trades, equity, times, entry_i, i, None, None,
                                    "L" if pos == 1 else "S", entry_price,
                                    fill, pos, commission, leverage, slippage=slippage)
            pos = 0; armed = False; stop = math.inf; best = math.nan
            m_armed = False; m_stop = math.inf
        # --- 1c. funding (hourly boundaries crossed while in position) ---
        if pos != 0 and funding_hour > 0:
            t0 = int(times[i].value // 1_000_000)
            t1 = t0 + freq_ms
            crosses = int(t1 // 3_600_000) - int(t0 // 3_600_000)
            if crosses > 0:
                fee = crosses * funding_hour * leverage * equity
                equity -= fee
                funding_paid += fee
        # --- 2. signals at bar close (reverse = close at close + new entry) ---
        prev_ema = emas[i - 1] if i > 0 else math.nan
        prev_vwap = vwaps[i - 1] if i > 0 else math.nan
        if not math.isnan(prev_ema) and not math.isnan(prev_vwap):
            if long_sig_ov is not None:
                long_sig = bool(long_sig_ov[i])
                short_sig = bool(short_sig_ov[i])
            else:
                long_sig = prev_ema < prev_vwap and ema_i >= vwap_i
                short_sig = prev_ema > prev_vwap and ema_i <= vwap_i
            if long_sig and short_sig:
                long_sig = short_sig = False
            blocked = (atr_pcts is not None and atr_pcts[i] < vol_min_ratio * vol_meds[i]) or \
                       (ema_trends is not None and (
                            (long_sig and c < ema_trends[i]) or
                            (short_sig and c > ema_trends[i])))
            if blocked:
                long_sig = short_sig = False
            if pos == 0 and long_sig and direction in ("both", "long"):
                pos = 1; entry_price = c; entry_i = i
                armed = False; stop = math.inf; best = c
                m_armed = False; m_stop = math.inf
                entered_this_bar = True
            elif pos == 0 and short_sig and direction in ("both", "short"):
                pos = -1; entry_price = c; entry_i = i
                armed = False; stop = math.inf; best = c
                m_armed = False; m_stop = math.inf
                entered_this_bar = True
            elif pos == 1 and short_sig and direction in ("both", "short"):
                equity = close_position(trades, equity, times, entry_i, i,
                                        None, None, "L", entry_price, c,
                                        1, commission, leverage, slippage=slippage)
                pos = -1; entry_price = c; entry_i = i
                armed = False; stop = math.inf; best = c
                m_armed = False; m_stop = math.inf
                entered_this_bar = True
            elif pos == -1 and long_sig and direction in ("both", "long"):
                equity = close_position(trades, equity, times, entry_i, i,
                                        None, None, "S", entry_price, c,
                                        -1, commission, leverage, slippage=slippage)
                pos = 1; entry_price = c; entry_i = i
                armed = False; stop = math.inf; best = c
                m_armed = False; m_stop = math.inf
                entered_this_bar = True
        # --- 3. ratchet (only for positions that existed before this bar) ---
        if pos != 0 and not entered_this_bar:
            if pos == 1:
                if trail == "high":
                    best = max(best, h)
                    if best - T > stop:
                        stop = best - T
                else:  # close-based ratchet (their canon example)
                    stop = max(stop, c - T)
            else:
                if trail == "high":
                    best = min(best, lo)
                    if best + T < stop:
                        stop = best + T
                else:
                    stop = min(stop, c + T)

    if pos != 0:
        c = closes[n - 1]
        equity = close_position(trades, equity, times, entry_i, n - 1,
                                None, None, "L" if pos == 1 else "S",
                                entry_price, c, pos, commission, leverage, slippage=slippage)
    return trades, equity, start_capital, funding_paid


def metrics(trades, end_equity, start_capital):
    tdf = pd.DataFrame(trades)
    if tdf.empty:
        return {"trades": 0}
    wins = tdf[tdf["pnl_usd"] > 0]
    losses = tdf[tdf["pnl_usd"] <= 0]
    gross_profit = wins["pnl_usd"].sum()
    gross_loss = -losses["pnl_usd"].sum()
    rets = tdf["pnl_usd"] / tdf["equity"].shift(1).fillna(start_capital)
    sr = rets.mean() / rets.std() * math.sqrt(len(tdf)) if rets.std() > 0 else 0
    eq_cum = start_capital + tdf["pnl_usd"].cumsum()
    dd = (eq_cum - eq_cum.cummax()) / eq_cum.cummax()
    dd_min = float(dd.min()) if len(dd) else 0.0
    return {
        "trades": len(tdf),
        "win_rate_pct": round(100 * len(wins) / len(tdf), 2),
        "gross_profit_usd": round(gross_profit, 2),
        "gross_loss_usd": round(gross_loss, 2),
        "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss > 0 else None,
        "net_pct": round(100 * (end_equity / start_capital - 1), 2),
        "max_drawdown_pct": round(100 * dd_min, 2),
        "sharpe_trades": round(sr, 2),
        "avg_bars": round(tdf["bars"].mean(), 1),
        "avg_win_usd": round(wins["pnl_usd"].mean(), 2) if len(wins) else 0,
        "avg_loss_usd": round(losses["pnl_usd"].mean(), 2) if len(losses) else 0,
        "end_equity_usd": round(end_equity, 2),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--ema", type=int, default=5)
    ap.add_argument("--atr-len", type=int, default=14)
    ap.add_argument("--mult", type=float, default=0.02)
    ap.add_argument("--vwap", default="daily")
    ap.add_argument("--trail", default="high", choices=["high", "close"])
    ap.add_argument("--double", action="store_true",
                    help="mirror second exit order applied to position")
    ap.add_argument("--commission", type=float, default=0.0005)
    ap.add_argument("--funding-hour", type=float, default=0.0,
                    help="funding rate per hour while in position (e.g. 0.0000125)")
    ap.add_argument("--dir", default="both", choices=["both", "long", "short"])
    ap.add_argument("--slippage", type=float, default=0.0,
                    help="per-side adverse fill fraction (e.g. 0.001 = 0.1%)")
    ap.add_argument("--vol-min", type=float, default=0.0,
                    help="skip entries when ATR%% below ratio x rolling median")
    ap.add_argument("--trend", type=int, default=0,
                    help="require close > EMA(n) for longs (mirror for shorts)")
    ap.add_argument("--window", default=None, help="YYYY-MM-DD:YYYY-MM-DD")
    ap.add_argument("--tag", default="run")
    ap.add_argument("--outdir", default="output")
    args = ap.parse_args()

    df = load(args.csv)
    if args.window:
        a, b = args.window.split(":")
        df = df[(df["ts"] >= pd.Timestamp(a, tz="UTC")) &
                (df["ts"] < pd.Timestamp(b, tz="UTC"))].reset_index(drop=True)
    print(f"bars={len(df)}  {df['ts'].iloc[0]} -> {df['ts'].iloc[-1]}")

    trades, end_equity, start_cap, funding_paid = run(
        df, ema_len=args.ema, atr_mult=args.mult, vwap_mode=args.vwap,
        atr_len=args.atr_len, trail=args.trail, double_exit=args.double,
        commission=args.commission, funding_hour=args.funding_hour,
        direction=args.dir, slippage=args.slippage,
        vol_min_ratio=args.vol_min, trend_len=args.trend)
    m = metrics(trades, end_equity, start_cap)
    m["funding_paid_usd"] = round(funding_paid, 2)
    print(json.dumps(m, indent=2))

    os.makedirs(args.outdir, exist_ok=True)
    pd.DataFrame(trades).to_csv(f"{args.outdir}/trades_{args.tag}.csv", index=False)
    with open(f"{args.outdir}/metrics.json", "a") as f:
        f.write(json.dumps({"tag": args.tag, "ema": args.ema,
                            "mult": args.mult, "vwap": args.vwap,
                            "trail": args.trail, **m}) + "\n")


if __name__ == "__main__":
    main()
