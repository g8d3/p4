#!/usr/bin/env python3
"""ag-03-cond: conditional next-candle tail analysis.

Compares the next-candle return distribution after a signal vs the
unconditional distribution, per (coin, tf), plus a pooled z-score version
(coin="ALL") used for robust verdicts where single-coin samples are thin.

Signals:
  prev_ret_gt_2s   : ret[t] >  +2 sigma
  prev_ret_lt_m2s  : ret[t] <  -2 sigma
  prev_ret_gt_3s   : ret[t] >  +3 sigma
  prev_ret_lt_m3s  : ret[t] <  -3 sigma
  range_top10      : range[t] in top decile
  range_top1       : range[t] in top percentile
  vol_top1         : v[t]     in top percentile
  up5_consec       : 5 consecutive up candles ending at t
  dn5_consec       : 5 consecutive down candles ending at t
  base             : unconditional (all rows)
"""
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

SRC = "../ag-01-data/output/candles_raw.csv"
OUT = "output/cond_next.csv"

SIGNALS = [
    "prev_ret_gt_2s", "prev_ret_lt_m2s", "prev_ret_gt_3s", "prev_ret_lt_m3s",
    "range_top10", "range_top1", "vol_top1", "up5_consec", "dn5_consec",
]
QUANTS = [0.50, 0.90, 0.99, 0.999]


def quantile_pct(s, q):
    return float(np.quantile(np.asarray(s, dtype=float), q))


def stat_block(y):
    """Return dict of next-return stats for a group."""
    y = np.asarray(y, dtype=float)
    y = y[~np.isnan(y)]
    n = int(len(y))
    if n == 0:
        return {"n": 0, "mean_next": np.nan, "stdev_next": np.nan,
                "p50_next": np.nan, "p90_next": np.nan, "p99_next": np.nan,
                "p99.9_next": np.nan}
    return {"n": n,
            "mean_next": float(y.mean()),
            "stdev_next": float(y.std(ddof=1)),
            "p50_next": quantile_pct(y, 0.50),
            "p90_next": quantile_pct(y, 0.90),
            "p99_next": quantile_pct(y, 0.99),
            "p99.9_next": quantile_pct(y, 0.999)}


def bootstrap_p99_ci(y, q=0.99, n_iter=2000, seed=42):
    """Percentile bootstrap CI for a tail quantile of group y."""
    y = np.asarray(y, dtype=float)
    y = y[~np.isnan(y)]
    n = len(y)
    if n < 10:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_iter, n))
    qs = np.quantile(y[idx], q, axis=1)
    return float(np.percentile(qs, 2.5)), float(np.percentile(qs, 97.5))


def mw_p(yes, no):
    yes = np.asarray(yes, dtype=float); yes = yes[~np.isnan(yes)]
    no = np.asarray(no, dtype=float); no = no[~np.isnan(no)]
    if len(yes) < 5 or len(no) < 5:
        return np.nan
    try:
        return float(mannwhitneyu(yes, no, alternative="two-sided").pvalue)
    except Exception:
        return np.nan


def main():
    df = pd.read_csv(SRC)
    df = df.sort_values(["coin", "tf", "t_ms"]).reset_index(drop=True)

    g = df.groupby(["coin", "tf"], sort=False)
    df["ret"] = g["c"].transform(lambda s: s.pct_change() * 100.0)
    df["range"] = (df["h"] - df["l"]) / df["l"] * 100.0
    df["ret_next"] = g["ret"].shift(-1)
    df["sigma"] = g["ret"].transform("std")
    df["ct"] = df["coin"] + "|" + df["tf"]

    # drop first candle per group (no ret) and last candle (no ret_next)
    df = df[df["ret"].notna()].copy()
    df = df[df["ret_next"].notna()].copy()

    # --- signals -------------------------------------------------------
    df["prev_ret_gt_2s"] = df["ret"] > 2.0 * df["sigma"]
    df["prev_ret_lt_m2s"] = df["ret"] < -2.0 * df["sigma"]
    df["prev_ret_gt_3s"] = df["ret"] > 3.0 * df["sigma"]
    df["prev_ret_lt_m3s"] = df["ret"] < -3.0 * df["sigma"]

    gr = df.groupby(["coin", "tf"], sort=False)["range"]
    df["range_top10"] = df["range"] >= gr.transform(lambda s: s.quantile(0.90))
    df["range_top1"] = df["range"] >= gr.transform(lambda s: s.quantile(0.99))
    gv = df.groupby(["coin", "tf"], sort=False)["v"]
    df["vol_top1"] = df["v"] >= gv.transform(lambda s: s.quantile(0.99))

    grt = df.groupby("ct", sort=False)["ret"]
    up5 = grt.apply(lambda s: (s > 0).rolling(5, min_periods=5).sum().eq(5))
    dn5 = grt.apply(lambda s: (s < 0).rolling(5, min_periods=5).sum().eq(5))
    df["up5_consec"] = up5.values
    df["dn5_consec"] = dn5.values

    # --- per-(coin,tf) table ------------------------------------------
    rows = []
    keys = []
    for (coin, tf), sub in df.groupby(["coin", "tf"], sort=False):
        y_all = sub["ret_next"]
        base = stat_block(y_all)
        rows.append({"coin": coin, "tf": tf, "signal": "base", "group": "base",
                     **base, "mw_p": np.nan, "p99_ci_lo": np.nan, "p99_ci_hi": np.nan})
        keys.append((coin, tf, "base"))
        for sig in SIGNALS:
            mask = sub[sig].astype(bool)
            yes = sub.loc[mask, "ret_next"]
            no = sub.loc[~mask, "ret_next"]
            by = stat_block(yes)
            bn = stat_block(no)
            ci_lo, ci_hi = bootstrap_p99_ci(yes.values, 0.99)
            rows.append({"coin": coin, "tf": tf, "signal": sig, "group": "yes",
                         **by, "mw_p": mw_p(yes.values, no.values),
                         "p99_ci_lo": ci_lo, "p99_ci_hi": ci_hi})
            rows.append({"coin": coin, "tf": tf, "signal": sig, "group": "no",
                         **bn, "mw_p": np.nan, "p99_ci_lo": np.nan, "p99_ci_hi": np.nan})
            keys.append((coin, tf, sig))

    # --- pooled z-score analysis (coin=ALL) ---------------------------
    # normalize returns to z per (coin,tf); pooled within a tf
    m = df.groupby(["coin", "tf"], sort=False)["ret"].transform("mean")
    df["z_next"] = (df["ret_next"] - m) / df["sigma"]

    for tf in sorted(df["tf"].unique()):
        sub = df[df["tf"] == tf]
        y_all = sub["z_next"]
        base = stat_block(y_all)
        rows.append({"coin": "ALL", "tf": tf, "signal": "base", "group": "base",
                     **base, "mw_p": np.nan, "p99_ci_lo": np.nan, "p99_ci_hi": np.nan})
        for sig in SIGNALS:
            mask = sub[sig].astype(bool)
            yes = sub.loc[mask, "z_next"]
            no = sub.loc[~mask, "z_next"]
            by = stat_block(yes)
            bn = stat_block(no)
            ci_lo, ci_hi = bootstrap_p99_ci(yes.values, 0.99)
            rows.append({"coin": "ALL", "tf": tf, "signal": sig, "group": "yes",
                         **by, "mw_p": mw_p(yes.values, no.values),
                         "p99_ci_lo": ci_lo, "p99_ci_hi": ci_hi})
            rows.append({"coin": "ALL", "tf": tf, "signal": sig, "group": "no",
                         **bn, "mw_p": np.nan, "p99_ci_lo": np.nan, "p99_ci_hi": np.nan})

    out = pd.DataFrame(rows)
    out = out[["coin", "tf", "signal", "group", "n", "mean_next", "stdev_next",
               "p50_next", "p90_next", "p99_next", "p99.9_next",
               "mw_p", "p99_ci_lo", "p99_ci_hi"]]
    out.to_csv(OUT, index=False)

    # --- |ret_next| extra stats for vol/range/vol signals (report) ----
    abs_stats = []
    for sig in ["range_top10", "range_top1", "vol_top1", "prev_ret_gt_2s",
                "prev_ret_lt_m2s", "prev_ret_gt_3s", "prev_ret_lt_m3s"]:
        for tf in sorted(df["tf"].unique()):
            sub = df[df["tf"] == tf]
            mask = sub[sig].astype(bool)
            a_yes = sub.loc[mask, "ret_next"].abs()
            a_base = sub["ret_next"].abs()
            if len(a_yes) == 0:
                continue
            abs_stats.append({
                "tf": tf, "signal": sig, "n_yes": len(a_yes),
                "mean_abs_yes": float(a_yes.mean()),
                "mean_abs_base": float(a_base.mean()),
                "ratio": float(a_yes.mean() / a_base.mean()),
            })
    pd.DataFrame(abs_stats).to_csv("output/abs_next.csv", index=False)

    # --- headline summary printed to stdout ---------------------------
    print("rows written:", len(out))
    print("signals:", SIGNALS)
    print("per-coin sample sizes (min yes-group n across signals):")
    smry = out[(out.group == "yes") & (out.coin != "ALL")].groupby(
        ["coin", "tf"])["n"].min()
    print(smry.to_string())


if __name__ == "__main__":
    main()
