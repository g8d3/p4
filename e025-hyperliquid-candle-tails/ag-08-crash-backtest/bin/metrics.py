#!/usr/bin/env python3
"""ag-08 — metrics + equity curves + charts + report tables.

Builds per-coin daily return series (0 = cash when flat) over each coin's OOS
window, pools them equal-weight per calendar day, and computes:
total return, expectancy (mean P&L per trade), win rate, max drawdown,
Sharpe-style (annualized daily mean/std) — gross, net-taker, net-maker.
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

RULES = [("down", 5), ("up", 5), ("down", 3), ("down", 10)]
RULE_LABEL = {("down", 5): "A (crash, hold 5)",
              ("up", 5): "B (rally, hold 5)",
              ("down", 3): "A sens. hold 3",
              ("down", 10): "A sens. hold 10",
              ("C", 1): "C (always long)"}


def main():
    df = pd.read_csv(CANDLES)
    d1 = df[df.tf == "1d"].copy()
    d1 = d1[d1.v > 0]
    bt = pd.read_csv(BT)
    oos = pd.read_csv(OOS)
    oos["oos_start_dt"] = pd.to_datetime(oos.oos_start, unit="ms")
    oos["oos_end_dt"] = pd.to_datetime(oos.oos_end, unit="ms")

    # ---- per-coin daily candle series (close-to-close daily return) ----
    coin_daily = {}
    coin_first = {}
    for coin in COINS_ORDER:
        g = d1[d1.coin == coin].sort_values("t_ms").reset_index(drop=True)
        g["ret"] = g["c"].pct_change()
        g["day"] = pd.to_datetime(g["t_ms"], unit="ms").dt.tz_localize(None)
        coin_daily[coin] = g[["day", "ret"]].copy()
        half = len(g) // 2
        coin_first[coin] = g.iloc[half]["day"]  # first OOS day

    # ---- daily net return series per coin per rule ----
    daily = {}  # (rule, hold) -> {coin: Series(net daily ret, indexed by day)}
    for (rule, hold) in RULES:
        t = bt[(bt.rule == rule) & (bt.hold == hold)]
        d = {}
        for coin in COINS_ORDER:
            sub = t[t.coin == coin]
            cd = coin_daily[coin].set_index("day")["ret"].copy()
            net = pd.Series(0.0, index=cd.index)
            for _, tr in sub.iterrows():
                e = pd.Timestamp(tr["entry_t"], unit="ms")
                x = pd.Timestamp(tr["exit_t"], unit="ms")
                # days where the position earns: (entry, exit] in candle-day terms
                mask = (cd.index > e) & (cd.index <= x)
                days = cd.index[mask]
                if len(days) == 0:
                    continue
                net.loc[days] = cd.loc[days].values
                # fees: entry day = first holding day, exit day = last
                net.loc[days[0]] = (1 + net.loc[days[0]]) * (1 - FEE_TAKER) - 1
                net.loc[days[-1]] = (1 + net.loc[days[-1]]) * (1 - FEE_TAKER) - 1
            d[coin] = net
        daily[("A" if rule == "down" else "B", hold)] = d

    # Rule C: always long, buy close->sell next close, fee both sides per day
    tC = bt[(bt.rule == "C")]
    dC = {}
    for coin in COINS_ORDER:
        cd = coin_daily[coin].set_index("day")["ret"].copy()
        first = coin_first[coin]
        net = cd.copy()
        net.loc[:] = (1 + net) * (1 - FEE_TAKER) ** 2 - 1
        net[net.index < first] = 0.0  # outside OOS
        dC[coin] = net
    daily[("C", 1)] = dC

    # ---- market-pooled daily series (equal weight per day) ----
    all_days = pd.DatetimeIndex([])
    for coin in COINS_ORDER:
        all_days = all_days.union(coin_daily[coin]["day"])
    all_days = all_days.sort_values()

    alive = {coin: coin_daily[coin]["day"].max() for coin in COINS_ORDER}
    n_alive = pd.Series(
        [sum(1 for c in COINS_ORDER if alive[c] >= day and coin_first[c] <= day)
         for day in all_days], index=all_days)
    pooled = {}
    for key, d in daily.items():
        pooled[key] = pd.Series(np.nan, index=all_days)
        for coin in COINS_ORDER:
            first = coin_first[coin]
            s = d[coin]
            s = s[s.index >= first]
            pooled[key] = pooled[key].add(s, fill_value=0.0)
        # equal weight per day over coins alive that day
        pooled[key] = pooled[key] / n_alive.replace(0, np.nan)

    # ---- metrics ----
    feemap = {"gross": 0.0, "taker": FEE_TAKER, "maker": FEE_MAKER}
    metrics = {}
    trade_metrics = {}
    for key in [("A", 5), ("B", 5), ("C", 1), ("A", 3), ("A", 10)]:
        label = RULE_LABEL[key]
        rule, hold = key
        rule_str = {"A": "down", "B": "up", "C": "C"}[rule]
        t = bt[(bt.rule == rule_str) & (bt.hold == hold)]
        trade_metrics[label] = {
            "n": len(t),
            "gross_mean": t["gross"].mean() * 100,
            "taker_mean": t["net_taker"].mean() * 100,
            "maker_mean": t["net_maker"].mean() * 100,
            "gross_win": (t["gross"] > 0).mean() * 100,
            "taker_win": (t["net_taker"] > 0).mean() * 100,
        }
        for fname, fee in feemap.items():
            col = "gross" if fname == "gross" else ("net_taker" if fname == "taker" else "net_maker")
            s = _build_pooled(bt, rule_str, hold, coin_daily, coin_first, fee, COINS_ORDER)
            eq = (1 + s.fillna(0.0)).cumprod()
            mdd = _max_dd(eq)
            daily_r = s.dropna()
            sharpe = (daily_r.mean() / daily_r.std() * np.sqrt(365)
                      if len(daily_r) > 1 and daily_r.std() > 0 else np.nan)
            metrics[(label, fname)] = {
                "total_return": (eq.iloc[-1] - 1) * 100,
                "expectancy": t[col].mean() * 100,
                "win_rate": (t[col] > 0).mean() * 100,
                "max_drawdown": mdd * 100,
                "sharpe": sharpe,
                "n_days": int(len(daily_r)),
            }

    # ---- per-coin trade stats (Rule A hold 5) ----
    per_coin = []
    for coin in COINS_ORDER:
        row = {"coin": coin}
        for key, col in [("A5", "gross"), ("A5n", "net_taker"),
                         ("B5", "gross"), ("C", "gross")]:
            if key == "A5":
                t = bt[(bt.rule == "down") & (bt.hold == 5) & (bt.coin == coin)]
            elif key == "A5n":
                t = bt[(bt.rule == "down") & (bt.hold == 5) & (bt.coin == coin)]
                row["A5_net"] = t["net_taker"].mean() * 100 if len(t) else np.nan
                row["A5_n"] = len(t)
                row["A5_win"] = (t["net_taker"] > 0).mean() * 100 if len(t) else np.nan
                continue
            elif key == "B5":
                t = bt[(bt.rule == "up") & (bt.hold == 5) & (bt.coin == coin)]
                row["B5_n"] = len(t)
                row["B5"] = t["gross"].mean() * 100 if len(t) else np.nan
                continue
            else:
                t = bt[(bt.rule == "C") & (bt.coin == coin)]
                row["C_days"] = len(t)
                row["C"] = t["gross"].mean() * 100 if len(t) else np.nan
                continue
            row["A5_n"] = len(t)
            row["A5"] = t["gross"].mean() * 100 if len(t) else np.nan
        per_coin.append(row)
    pc = pd.DataFrame(per_coin)
    pc.to_csv("output/per_coin.csv", index=False)

    with open("output/metrics.json", "w") as f:
        json.dump({"metrics": {f"{k[0]}::{k[1]}": v for k, v in metrics.items()},
                   "trade_metrics": trade_metrics},
                  f, indent=2, default=float)

    # ---- equity curves for chart (net of taker fees) ----
    eq_curves = {}
    for key in [("A", 5), ("B", 5), ("C", 1), ("A", 3), ("A", 10)]:
        rule_str = {"A": "down", "B": "up", "C": "C"}[key[0]]
        s = _build_pooled(bt, rule_str, key[1], coin_daily, coin_first, FEE_TAKER, COINS_ORDER)
        eq_curves[RULE_LABEL[key]] = (1 + s.fillna(0.0)).cumprod()
    eq_df = pd.DataFrame(eq_curves)
    eq_df.to_csv("output/equity_daily.csv")

    # report summary
    for key in [("A", 5), ("B", 5), ("C", 1), ("A", 3), ("A", 10)]:
        label = RULE_LABEL[key]
        m = metrics[(label, "taker")]
        print(f"{label:24s} n={trade_metrics[label]['n']:4d} "
              f"total {m['total_return']:7.2f}%  exp {m['expectancy']:6.3f}%  "
              f"win {m['win_rate']:5.1f}%  mdd {m['max_drawdown']:7.2f}%  "
              f"sharpe {m['sharpe']:.2f}")


def _build_pooled(bt, rule, hold, coin_daily, coin_first, fee, coins):
    """Pooled daily net return series for a rule with a given fee."""
    t = bt[(bt.rule == rule) & (bt.hold == hold)]
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
        first = coin_first[coin]
        s = net[net.index >= first]
        pooled = pooled.add(s, fill_value=0.0)
    return pooled / n_alive.replace(0, np.nan)


def _max_dd(eq):
    peak = eq.cummax()
    return (eq / peak - 1.0).min()


if __name__ == "__main__":
    main()
