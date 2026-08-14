#!/usr/bin/env python3
"""ag-15 — OOS backtest of the COMBINED reversion strategy (T1 OR T2).

T1 (crash, ag-08): ret < -3*sigma, sigma from FIRST half only.
T2 (low-volume down, ag-14): ret < 0 AND |vol_adj| in the top quintile of
   |vol_adj| among down moves; median_v and the q5 cutoff from FIRST half only.

Rules (grid fixed BEFORE results):
  A = T1 only        B = T2 only        C = T1 OR T2        D = T1 AND T2
  E = always long baseline (buy close, sell next close)
A/B/C/D hold 5 daily candles; E holds 1. One position per coin at a time.
Triggers detected and traded on the SECOND half only. P&L = (c[exit]-c[entry])
/ c[entry]; the trigger candle's own return is NOT part of the trade.
"""
import pandas as pd
import numpy as np

CANDLES = "../ag-01-data/output/candles_raw.csv"
OUT = "output/backtest.csv"
OOS_OUT = "output/oos_windows.csv"
OVERLAP_OUT = "output/trigger_overlap.csv"

FEE_TAKER = 0.00045   # each side
FEE_MAKER = 0.00018   # each side
HOLD = 5              # daily candles for A/B/C/D

COINS_ORDER = ["BTC", "ETH", "HYPE", "SOL", "PUMP", "ZEC", "XRP",
               "LIT", "DOGE", "CRV", "AAVE", "XMR"]

RULE_NAME = {"A": "A (T1 crash only)", "B": "B (T2 low-vol down only)",
             "C": "C (T1 OR T2)", "D": "D (T1 AND T2)",
             "E": "E (always long baseline)"}


def net_ret(gross, fee):
    """Multiplicative net return for a round trip (entry fee + exit fee)."""
    return (1.0 + gross) * (1.0 - fee) * (1.0 - fee) - 1.0


def compute_coin(g):
    """Per-coin 1d series -> (events, trades for every rule).

    g: DataFrame for one coin, 1d, v>0, sorted by t_ms, with 'ret' (pct).
    Returns dict with event masks and rule trades.
    """
    n = len(g)
    half = n // 2
    ret = g["ret"].values
    c = g["c"].values
    v = g["v"].values

    first = g.iloc[:half]
    sigma = first["ret"].std(ddof=1) if half > 1 else np.nan

    # median_v: causal trailing rolling median of v (window 101, min_periods 30,
    # the same window ag-14 used for its causal volume percentile). This is the
    # walk-forward analog of ag-14's full-series median: a static FIRST-half
    # median is a terrible baseline because volumes grew 10-20x over the sample
    # (BTC 1.4k -> 29k), making second-half |vol_adj| tiny and T2 never fire.
    # Rolling median keeps vol_adj scale comparable across halves.
    med_v = pd.Series(v).rolling(101, min_periods=30).median().values

    # vol_adj in % per unit of relative volume (ag-14): ret / (v/median_v)
    rel_vol = v / med_v
    with np.errstate(divide="ignore", invalid="ignore"):
        vol_adj = np.where(np.isfinite(rel_vol) & (rel_vol != 0), ret / rel_vol, np.nan)

    # q5 cutoff over FIRST-half down moves (80th pct of |vol_adj|)
    first_mask = np.zeros(n, bool); first_mask[:half] = True
    first_down = (first_mask) & (ret < 0) & np.isfinite(vol_adj)
    q5_thresh = np.nanpercentile(np.abs(vol_adj[first_down]), 80.0)

    # event masks (whole series; only the second half is traded)
    t1 = np.zeros(n, bool)
    t2 = np.zeros(n, bool)
    valid = np.isfinite(ret) & np.isfinite(vol_adj)
    t1[valid] = ret[valid] < -3.0 * sigma
    t2[valid] = (ret[valid] < 0.0) & (np.abs(vol_adj[valid]) >= q5_thresh)

    events = {"sigma": sigma, "med_v": first["v"].median(), "q5_thresh": q5_thresh,
              "n_first": half, "n_second": n - half}

    # ---- trades ----
    def scan(trigger_mask, rule, hold):
        trades = []
        open_until = -1
        for i in range(half, n):
            if i <= open_until or not trigger_mask[i]:
                continue
            exit_idx = i + hold
            if exit_idx >= n:
                break  # cannot complete the hold
            gross = (c[exit_idx] - c[i]) / c[i]
            ttype = "T1" if t1[i] else ("T2" if t2[i] else "T2")
            if t1[i] and t2[i]:
                ttype = "T1+T2"
            trades.append({
                "coin": g.iloc[i]["coin"], "rule": rule, "hold": hold,
                "entry_idx": i, "entry_t": int(g.iloc[i]["t_ms"]),
                "exit_idx": exit_idx, "exit_t": int(g.iloc[exit_idx]["t_ms"]),
                "gross": gross, "net_taker": net_ret(gross, FEE_TAKER),
                "net_maker": net_ret(gross, FEE_MAKER),
                "trigger": ttype, "trigger_ret_pct": ret[i],
                "trigger_vol_adj": vol_adj[i],
            })
            open_until = exit_idx
        return trades

    trades = []
    trades += scan(t1, "A", HOLD)
    trades += scan(t2, "B", HOLD)
    trades += scan(t1 | t2, "C", HOLD)
    trades += scan(t1 & t2, "D", HOLD)

    # E (baseline): long every day in the second half — no single-position
    # blocking (sell at close[i+1] and immediately buy at close[i+1] is one
    # clean round trip; ag-08's rule C does the same).
    for i in range(half, n - 1):
        gross = (c[i + 1] - c[i]) / c[i]
        trades.append({
            "coin": g.iloc[i]["coin"], "rule": "E", "hold": 1,
            "entry_idx": i, "entry_t": int(g.iloc[i]["t_ms"]),
            "exit_idx": i + 1, "exit_t": int(g.iloc[i + 1]["t_ms"]),
            "gross": gross, "net_taker": net_ret(gross, FEE_TAKER),
            "net_maker": net_ret(gross, FEE_MAKER),
            "trigger": "-", "trigger_ret_pct": np.nan, "trigger_vol_adj": np.nan,
        })

    # overlap stats (second half only)
    t1o = t1[half:].sum(); t2o = t2[half:].sum()
    both = (t1 & t2)[half:].sum()
    overlap = {"coin": g.iloc[0]["coin"],
               "T1_count": int(t1o), "T2_count": int(t2o),
               "both_count": int(both),
               "frac_T2_also_T1": both / t2o if t2o else np.nan,
               "frac_T1_also_T2": both / t1o if t1o else np.nan,
               "T1_and_T2_independent_frac": float((t1 & t2)[half:].mean())}

    return events, trades, overlap


def main():
    df = pd.read_csv(CANDLES)
    d1 = df[df.tf == "1d"].copy()
    d1 = d1[d1.v > 0]
    rows = []
    oos_info = []
    overlap_rows = []
    for coin in COINS_ORDER:
        g = d1[d1.coin == coin].sort_values("t_ms").reset_index(drop=True)
        g["ret"] = g["c"].pct_change() * 100.0   # % close-to-close
        events, trades, overlap = compute_coin(g)
        rows.extend(trades)
        n = len(g)
        half = n // 2
        second = g.iloc[half:]
        oos_info.append({
            "coin": coin, "n": n,
            "first_half_n": half, "second_half_n": n - half,
            "sigma": events["sigma"], "median_v": events["med_v"],
            "q5_thresh_vol_adj": events["q5_thresh"],
            "oos_start": int(second.iloc[0]["t_ms"]),
            "oos_end": int(second.iloc[-1]["t_ms"]),
        })
        overlap_rows.append(overlap)

    bt = pd.DataFrame(rows)
    bt["entry_date"] = pd.to_datetime(bt.entry_t, unit="ms", utc=True).dt.date
    bt["exit_date"] = pd.to_datetime(bt.exit_t, unit="ms", utc=True).dt.date
    bt["rule_name"] = bt["rule"].map(RULE_NAME)
    bt["fee_taker_roundtrip"] = FEE_TAKER * 2
    bt["fee_maker_roundtrip"] = FEE_MAKER * 2
    bt["gross_pct"] = bt["gross"] * 100
    bt["net_taker_pct"] = bt["net_taker"] * 100
    bt["net_maker_pct"] = bt["net_maker"] * 100
    bt = bt.sort_values(["rule", "coin", "entry_t"]).reset_index(drop=True)
    bt.to_csv(OUT, index=False)

    oos = pd.DataFrame(oos_info)
    oos["oos_start_date"] = pd.to_datetime(oos.oos_start, unit="ms", utc=True).dt.date
    oos["oos_end_date"] = pd.to_datetime(oos.oos_end, unit="ms", utc=True).dt.date
    oos.to_csv(OOS_OUT, index=False)

    olap = pd.DataFrame(overlap_rows)
    olap.to_csv(OVERLAP_OUT, index=False)

    # quick summary + replication check vs ag-08
    for rule in ["A", "B", "C", "D", "E"]:
        sub = bt[bt.rule == rule]
        print(f"Rule {rule}: {len(sub)} trades, gross mean "
              f"{sub.gross.mean()*100:.3f}%, net_taker mean "
              f"{sub.net_taker.mean()*100:.3f}%, win "
              f"{((sub.net_taker > 0).mean()*100) if len(sub) else 0:.1f}%")
    print("\ntrigger overlap:\n", olap.to_string(index=False))
    print("\nwrote", OUT, OOS_OUT, OVERLAP_OUT)


if __name__ == "__main__":
    main()
