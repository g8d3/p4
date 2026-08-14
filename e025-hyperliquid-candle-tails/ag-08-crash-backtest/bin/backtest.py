#!/usr/bin/env python3
"""ag-08 — OOS backtest of daily crash reversion (walk-forward, net of fees).

Rule A (finding): buy at close of a 1d crash candle (ret < -3*sigma), hold H
  daily candles, sell at close. sigma computed ONLY on the first half of each
  coin's 1d series; events detected only in the second half.
Rule B (control): same but for rallies (ret > +3*sigma).
Rule C (baseline): always long every day (buy at close, sell at next close).
Sensitivity: H = 3 and 10 for Rule A.

P&L per trade = (close[exit] - close[entry]) / close[entry].
Crash candle's own return is NOT part of the trade (we enter at its close).
Single position rule: no re-entry while a position is open on the same coin.
"""
import pandas as pd
import numpy as np

CANDLES = "../ag-01-data/output/candles_raw.csv"
OUT = "output/backtest.csv"

FEE_TAKER = 0.00045   # each side
FEE_MAKER = 0.00018   # each side

COINS_ORDER = ["BTC", "ETH", "HYPE", "SOL", "PUMP", "ZEC", "XRP",
               "LIT", "DOGE", "CRV", "AAVE", "XMR"]

def net_ret(gross, fee):
    """Multiplicative net return for a round trip (entry fee + exit fee)."""
    return (1.0 + gross) * (1.0 - fee) * (1.0 - fee) - 1.0


def per_coin_trades(g, sigma, hold, side):
    """Scan second half of a coin's series, produce trades for one rule.

    g: DataFrame sorted by t_ms (1d, v>0), with 'ret' column.
    side: 'down' (Rule A, ret < -3*sigma) or 'up' (Rule B, ret > +3*sigma).
    Returns list of dicts: coin, rule, hold, entry_idx, entry_t, exit_idx,
    exit_t, gross, net_taker, net_maker.
    """
    n = len(g)
    half = n // 2
    trades = []
    open_until = -1  # index of the last exit; no new entry while idx <= open_until
    for i in range(half, n - 1):  # need at least one candle after entry
        if i <= open_until:
            continue
        r = g.iloc[i]["ret"]
        if np.isnan(r):
            continue
        hit = (r < -3.0 * sigma) if side == "down" else (r > 3.0 * sigma)
        if not hit:
            continue
        exit_idx = i + hold
        if exit_idx >= n:
            break  # cannot complete the hold — stop (rest of series is too short)
        entry_c = g.iloc[i]["c"]
        exit_c = g.iloc[exit_idx]["c"]
        gross = (exit_c - entry_c) / entry_c
        trades.append({
            "coin": g.iloc[i]["coin"],
            "rule": side, "hold": hold,
            "entry_idx": i, "entry_t": int(g.iloc[i]["t_ms"]),
            "exit_idx": exit_idx, "exit_t": int(g.iloc[exit_idx]["t_ms"]),
            "gross": gross,
            "net_taker": net_ret(gross, FEE_TAKER),
            "net_maker": net_ret(gross, FEE_MAKER),
        })
        open_until = exit_idx
    return trades


def rule_c_trades(g):
    """Baseline: long every day in the second half (buy close, sell next close)."""
    n = len(g)
    half = n // 2
    trades = []
    for i in range(half, n - 1):
        entry_c = g.iloc[i]["c"]
        exit_c = g.iloc[i + 1]["c"]
        gross = (exit_c - entry_c) / entry_c
        trades.append({
            "coin": g.iloc[i]["coin"],
            "rule": "C", "hold": 1,
            "entry_idx": i, "entry_t": int(g.iloc[i]["t_ms"]),
            "exit_idx": i + 1, "exit_t": int(g.iloc[i + 1]["t_ms"]),
            "gross": gross,
            "net_taker": net_ret(gross, FEE_TAKER),
            "net_maker": net_ret(gross, FEE_MAKER),
        })
    return trades


def main():
    df = pd.read_csv(CANDLES)
    d1 = df[df.tf == "1d"].copy()
    d1 = d1[d1.v > 0]
    rows = []
    oos_info = []
    for coin in COINS_ORDER:
        g = d1[d1.coin == coin].sort_values("t_ms").reset_index(drop=True)
        g["ret"] = g["c"].pct_change() * 100.0   # % return, close-to-close
        n = len(g)
        half = n // 2
        first = g.iloc[:half]
        second = g.iloc[half:].reset_index(drop=True)
        sigma = first["ret"].std(ddof=1) if half > 1 else np.nan
        # sigma from first half only — walk-forward
        assert second["ret"].isna().sum() == 0, f"{coin}: NaN in second half ret"
        oos_info.append({
            "coin": coin, "n": n, "first_half_n": half, "second_half_n": n - half,
            "sigma": sigma,
            "oos_start": int(second.iloc[0]["t_ms"]),
            "oos_end": int(second.iloc[-1]["t_ms"]),
        })
        for hold, side in [(5, "down"), (5, "up"), (3, "down"), (10, "down")]:
            rows.extend(per_coin_trades(g, sigma, hold, side))
        rows.extend(rule_c_trades(g))

    bt = pd.DataFrame(rows)
    bt["entry_date"] = pd.to_datetime(bt.entry_t, unit="ms", utc=True).dt.date
    bt["exit_date"] = pd.to_datetime(bt.exit_t, unit="ms", utc=True).dt.date
    bt = bt.sort_values(["rule", "hold", "coin", "entry_t"]).reset_index(drop=True)
    bt.to_csv(OUT, index=False)

    oos = pd.DataFrame(oos_info)
    oos["oos_start_date"] = pd.to_datetime(oos.oos_start, unit="ms", utc=True).dt.date
    oos["oos_end_date"] = pd.to_datetime(oos.oos_end, unit="ms", utc=True).dt.date
    oos.to_csv("output/oos_windows.csv", index=False)

    # quick summary
    for rule, hold in [("down", 5), ("up", 5), ("down", 3), ("down", 10), ("C", 1)]:
        sub = bt[(bt.rule == rule) & (bt.hold == hold)]
        print(f"Rule {rule} hold={hold}: {len(sub)} trades, "
              f"gross mean {sub.gross.mean()*100:.2f}%, "
              f"net_taker mean {sub.net_taker.mean()*100:.2f}%, "
              f"win {((sub.gross>0).mean()*100):.1f}%")
    print("wrote", OUT, "and output/oos_windows.csv")


if __name__ == "__main__":
    main()
