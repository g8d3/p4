#!/usr/bin/env python3
"""ag-15 — metrics + pooled equity for rules A/B/C/D/E.

Replicates ag-08/metrics.py methodology: per-coin daily net return series
(0 = cash when flat) over each coin's OOS window, pooled equal-weight per
calendar day over coins alive that day. Metrics: total return, expectancy,
win rate, max drawdown, Sharpe-style — gross, net-taker, net-maker.
"""
import pandas as pd
import numpy as np
import json

CANDLES = "../ag-01-data/output/candles_raw.csv"
BT = "output/backtest.csv"
OOS = "output/oos_windows.csv"

FEE_TAKER = 0.00045
FEE_MAKER = 0.00018
COINS_ORDER = ["BTC", "ETH", "HYPE", "SOL", "PUMP", "ZEC", "XRP",
               "LIT", "DOGE", "CRV", "AAVE", "XMR"]

RULES = ["A", "B", "C", "D", "E"]
RULE_HOLD = {"A": 5, "B": 5, "C": 5, "D": 5, "E": 1}


def main():
    df = pd.read_csv(CANDLES)
    d1 = df[df.tf == "1d"].copy()
    d1 = d1[d1.v > 0]
    bt = pd.read_csv(BT)
    oos = pd.read_csv(OOS)

    coin_daily = {}
    coin_first = {}
    for coin in COINS_ORDER:
        g = d1[d1.coin == coin].sort_values("t_ms").reset_index(drop=True)
        g["ret"] = g["c"].pct_change()
        g["day"] = pd.to_datetime(g["t_ms"], unit="ms").dt.tz_localize(None)
        coin_daily[coin] = g[["day", "ret"]].copy()
        half = len(g) // 2
        coin_first[coin] = g.iloc[half]["day"]

    all_days = pd.DatetimeIndex([])
    for coin in COINS_ORDER:
        all_days = all_days.union(coin_daily[coin]["day"])
    all_days = all_days.sort_values()

    alive = {coin: coin_daily[coin]["day"].max() for coin in COINS_ORDER}
    n_alive = pd.Series(
        [sum(1 for c in COINS_ORDER if alive[c] >= day and coin_first[c] <= day)
         for day in all_days], index=all_days)

    metrics = {}
    trade_metrics = {}
    eq_curves = {}

    for rule in RULES:
        hold = RULE_HOLD[rule]
        t = bt[bt.rule == rule]
        trade_metrics[rule] = {
            "n": len(t),
            "gross_mean": t["gross"].mean() * 100,
            "taker_mean": t["net_taker"].mean() * 100,
            "maker_mean": t["net_maker"].mean() * 100,
            "gross_win": (t["gross"] > 0).mean() * 100,
            "taker_win": (t["net_taker"] > 0).mean() * 100,
            "per_trade_sharpe_taker": (t["net_taker"].mean() / t["net_taker"].std()
                                       if len(t) > 1 and t["net_taker"].std() > 0 else np.nan),
        }
        for fname, fee in [("gross", 0.0), ("taker", FEE_TAKER), ("maker", FEE_MAKER)]:
            s = _build_pooled(bt, rule, hold, coin_daily, coin_first, fee, COINS_ORDER)
            eq = (1 + s.fillna(0.0)).cumprod()
            mdd = (eq / eq.cummax() - 1.0).min() * 100
            daily_r = s.dropna()
            sharpe = (daily_r.mean() / daily_r.std() * np.sqrt(365)
                      if len(daily_r) > 1 and daily_r.std() > 0 else np.nan)
            col = "gross" if fname == "gross" else ("net_taker" if fname == "taker" else "net_maker")
            metrics[(rule, fname)] = {
                "total_return": (eq.iloc[-1] - 1) * 100,
                "expectancy": t[col].mean() * 100,
                "win_rate": (t[col] > 0).mean() * 100,
                "max_drawdown": mdd,
                "sharpe": sharpe,
                "n_days": int(len(daily_r)),
            }
        # equity curve net of taker for the chart
        s = _build_pooled(bt, rule, hold, coin_daily, coin_first, FEE_TAKER, COINS_ORDER)
        eq_curves[rule] = (1 + s.fillna(0.0)).cumprod()

    # per-coin trade stats
    per_coin = []
    for coin in COINS_ORDER:
        row = {"coin": coin}
        for rule in RULES:
            t = bt[(bt.rule == rule) & (bt.coin == coin)]
            row[f"{rule}_n"] = len(t)
            row[f"{rule}_mean_net"] = t["net_taker"].mean() * 100 if len(t) else np.nan
            row[f"{rule}_win"] = (t["net_taker"] > 0).mean() * 100 if len(t) else np.nan
        per_coin.append(row)
    pc = pd.DataFrame(per_coin)
    pc.to_csv("output/per_coin.csv", index=False)

    with open("output/metrics.json", "w") as f:
        json.dump({"metrics": {f"{r}::{f}": v for (r, f), v in metrics.items()},
                   "trade_metrics": trade_metrics},
                  f, indent=2, default=float)

    eq_df = pd.DataFrame(eq_curves)
    eq_df.to_csv("output/equity_daily.csv")

    for rule in RULES:
        m = metrics[(rule, "taker")]
        tm = trade_metrics[rule]
        print(f"Rule {rule}: n={tm['n']:4d} total {m['total_return']:8.2f}% "
              f"exp {m['expectancy']:7.3f}% win {m['win_rate']:5.1f}% "
              f"mdd {m['max_drawdown']:8.2f}% sharpe {m['sharpe']:.2f}")


def _build_pooled(bt, rule, hold, coin_daily, coin_first, fee, coins):
    t = bt[bt.rule == rule]
    all_days = pd.DatetimeIndex([])
    for coin in coins:
        all_days = all_days.union(coin_daily[coin]["day"])
    all_days = all_days.sort_values()
    pooled = pd.Series(0.0, index=all_days)
    alive = {c: coin_daily[c]["day"].max() for c in coins}
    n_alive = pd.Series(
        [sum(1 for c in coins if alive[c] >= day and coin_first[c] <= day)
         for day in all_days], index=all_days)
    for coin in coins:
        cd = coin_daily[coin].set_index("day")["ret"].copy()
        net = pd.Series(0.0, index=cd.index)
        sub = t[t.coin == coin]
        for _, tr in sub.iterrows():
            e = pd.Timestamp(tr["entry_t"], unit="ms")
            x = pd.Timestamp(tr["exit_t"], unit="ms")
            mask = (cd.index > e) & (cd.index <= x)
            days = cd.index[mask]
            if len(days) == 0:
                continue
            net.loc[days] = cd.loc[days].values
            if fee > 0:
                net.loc[days[0]] = (1 + net.loc[days[0]]) * (1 - fee) - 1
                net.loc[days[-1]] = (1 + net.loc[days[-1]]) * (1 - fee) - 1
        s = net[net.index >= coin_first[coin]]
        pooled = pooled.add(s, fill_value=0.0)
    return pooled / n_alive.replace(0, np.nan)


if __name__ == "__main__":
    main()
