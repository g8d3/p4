import pandas as pd
import numpy as np
from scipy import stats

IN = "../ag-01-data/output/candles_raw.csv"
OUT_PATTERNS = "output/patterns.csv"
OUT_DETAIL = "output/bucket_detail.csv"
OUT_METRICS = "output/rep_metrics.csv"
OUT_HEAT = "output/heatmap_data.csv"
OUT_COIN = "output/patterns_by_coin.csv"
OUT_REP = "output/replication_rates.csv"

print("=== STEP 1/6: load ===")
df = pd.read_csv(IN)
df = df[df["v"] > 0]
df = df.sort_values(["coin", "tf", "t_ms"]).reset_index(drop=True)

print("=== STEP 2/6: derived columns ===")
g = df.groupby(["coin", "tf"], sort=False)
df["ret"] = g["c"].pct_change() * 100.0
df["range"] = (df["h"] - df["l"]) / df["l"] * 100.0
hl = df["h"] - df["l"]
df["body"] = np.where(hl > 0, (df["c"] - df["l"]) / np.where(hl > 0, hl, np.nan), np.nan)
df["sig"] = g["ret"].transform(lambda x: x.std(ddof=1))
df["big"] = df["ret"].abs() >= 2.0 * df["sig"]
df["vol_chg"] = g["v"].pct_change()
vol_per_move = df["v"] / df["ret"].abs()
df["vol_per_move"] = np.where(df["ret"].abs() > 1e-9, vol_per_move, np.nan)
df["v_prev"] = g["v"].shift(1)
ma20 = df.groupby(["coin", "tf"], sort=False)["v_prev"].rolling(20, min_periods=5).median()
df["vol_ma20"] = df["v"] / ma20.reset_index(level=[0, 1], drop=True)

print("=== STEP 3/6: calendar + shape feature buckets ===")
dt = pd.to_datetime(df["t_ms"], unit="ms", utc=True)
df["hour"] = dt.dt.hour.astype(int)
df["weekday"] = dt.dt.weekday.astype(int)
df["dom"] = dt.dt.day.astype(int)
df["hw"] = dt.dt.weekday.astype(int).astype(str) + "x" + dt.dt.hour.astype(int).astype(str)

def pct_bucket(s):
    r = s.rank(pct=True, method="average")
    return pd.cut(r, [-0.001, 0.5, 0.9, 0.99, 1.001], labels=["<50", "50-90", "90-99", ">99"])

df["vol_pct"] = g["v"].transform(pct_bucket)
df["vol_per_move_b"] = g["vol_per_move"].transform(pct_bucket)
df["vol_chg_b"] = g["vol_chg"].transform(lambda s: pd.qcut(s.rank(method="first"), 10, labels=["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10"]))
df["vol_ma20_b"] = pd.cut(df["vol_ma20"], [-np.inf, 0.5, 1.0, 2.0, 4.0, np.inf], labels=["<0.5x", "0.5-1x", "1-2x", "2-4x", ">4x"])
df["body_b"] = pd.cut(df["body"], [-np.inf, 0.15, 0.85, np.inf], labels=["lower", "mid", "upper"])

grpbig = df["big"].cumsum()
cnt = grpbig.groupby(grpbig).cumcount()
df["cooloff_b"] = np.select(
    [grpbig == 0, cnt == 0, cnt <= 2, cnt <= 5],
    ["never", "0", "1-2", "3-5"],
    default="6+",
)

print("=== STEP 4/6: next-period targets ===")
df["ret_next"] = g["ret"].shift(-1)
df["range_next"] = g["range"].shift(-1)
df["abs_next"] = df["ret_next"].abs()
df = df[df["ret_next"].notna()].copy()

for col in ["hour", "weekday", "dom"]:
    df[col] = df[col].astype("category")

FEATURES = {
    "hour": "hour",
    "weekday": "weekday",
    "dom": "dom",
    "vol_pct": "vol_pct",
    "vol_chg": "vol_chg_b",
    "vol_per_move": "vol_per_move_b",
    "vol_ma20": "vol_ma20_b",
    "body_pos": "body_b",
    "cooloff": "cooloff_b",
}

FEAT_ORDER = {
    "hour": [str(i) for i in range(24)],
    "weekday": [str(i) for i in range(7)],
    "dom": [str(i) for i in range(1, 32)],
    "vol_pct": ["<50", "50-90", "90-99", ">99"],
    "vol_chg": ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10"],
    "vol_per_move": ["<50", "50-90", "90-99", ">99"],
    "vol_ma20": ["<0.5x", "0.5-1x", "1-2x", "2-4x", ">4x"],
    "body_pos": ["lower", "mid", "upper"],
    "cooloff": ["never", "0", "1-2", "3-5", "6+"],
}

print("=== STEP 5/6: per-feature x tf aggregation + split halves ===")
med_t = df.groupby(["coin", "tf"])["t_ms"].transform("median")
df["half"] = np.where(df["t_ms"] <= med_t, "h1", "h2")

rows = []
for feat, col in FEATURES.items():
    for tf in sorted(df["tf"].unique()):
        sub = df[df["tf"] == tf]
        base = sub[col]
        known = base.notna()
        s = sub[known]
        for bucket, grp in s.groupby(base[known], observed=True):
            n = len(grp)
            rn = grp["ret_next"]
            an = grp["abs_next"]
            rnge = grp["range_next"]
            h1 = grp[grp["half"] == "h1"]["ret_next"]
            h2 = grp[grp["half"] == "h2"]["ret_next"]
            rows.append({
                "feature": feat,
                "bucket": str(bucket),
                "tf": tf,
                "n": n,
                "mean_next": rn.mean(),
                "median_next": rn.median(),
                "p90_next": an.quantile(0.90),
                "p99_next": an.quantile(0.99),
                "|mean|_next": an.mean(),
                "median_abs_next": an.median(),
                "range_median_next": rnge.median(),
                "range_p90_next": rnge.quantile(0.90),
                "split1_median": h1.median(),
                "split2_median": h2.median(),
                "h1_n": len(h1),
                "h2_n": len(h2),
            })

patterns = pd.DataFrame(rows)
patterns = patterns.dropna(subset=["median_abs_next"])
patterns["ord"] = patterns.apply(
    lambda r: FEAT_ORDER[r["feature"]].index(r["bucket"])
    if r["bucket"] in FEAT_ORDER[r["feature"]] else 999, axis=1)
patterns = patterns.sort_values(["feature", "tf", "ord"]).drop(columns=["ord"])
patterns.to_csv(OUT_PATTERNS, index=False)
print("patterns rows:", len(patterns))

metrics = []
for feat, col in FEATURES.items():
    for tf in sorted(df["tf"].unique()):
        sub = df[(df["tf"] == tf) & (df[col].notna())]
        if sub.empty:
            continue
        p = patterns[(patterns["feature"] == feat) & (patterns["tf"] == tf)]
        p = p[(p["h1_n"] >= 30) & (p["h2_n"] >= 30)]
        if len(p) < 3:
            metrics.append({"feature": feat, "tf": tf, "buckets": len(p), "dir_rho": np.nan, "dir_p": np.nan, "vol_rho": np.nan, "vol_p": np.nan, "dir_maxdev": np.nan, "vol_spread": np.nan, "overall_med": np.nan, "overall_absmed": np.nan})
            continue
        d1 = p["split1_median"].astype(float).values
        d2 = p["split2_median"].astype(float).values
        a1 = np.array([sub[(sub["half"] == "h1") & (sub[col].astype(str) == b)]["abs_next"].median() for b in p["bucket"]])
        a2 = np.array([sub[(sub["half"] == "h2") & (sub[col].astype(str) == b)]["abs_next"].median() for b in p["bucket"]])
        rho_d, p_d = stats.spearmanr(d1, d2)
        rho_a, p_a = stats.spearmanr(a1, a2)
        over_med = sub["ret_next"].median()
        over_abs = sub["abs_next"].median()
        maxdev = p["median_next"].sub(over_med).abs().max()
        spread = p["median_abs_next"].max() / p["median_abs_next"].min()
        metrics.append({"feature": feat, "tf": tf, "buckets": len(p), "dir_rho": rho_d, "dir_p": p_d, "vol_rho": rho_a, "vol_p": p_a, "dir_maxdev": maxdev, "vol_spread": spread, "overall_med": over_med, "overall_absmed": over_abs})

metrics_df = pd.DataFrame(metrics)
metrics_df.to_csv(OUT_METRICS, index=False)
print("metrics rows:", len(metrics_df))

print("=== STEP 6/7: per-coin patterns ===")
coin_rows = []
for coin in sorted(df["coin"].unique()):
    cdf = df[df["coin"] == coin]
    for feat, col in FEATURES.items():
        for tf in sorted(cdf["tf"].unique()):
            sub = cdf[cdf["tf"] == tf]
            base = sub[col]
            known = base.notna()
            s = sub[known]
            for bucket, grp in s.groupby(base[known], observed=True):
                n = len(grp)
                if n < 30:
                    continue
                rn = grp["ret_next"]
                an = grp["abs_next"]
                rnge = grp["range_next"]
                q90 = an.quantile(0.90) if n >= 300 else np.nan
                q99 = an.quantile(0.99) if n >= 300 else np.nan
                coin_rows.append({
                    "coin": coin,
                    "feature": feat,
                    "bucket": str(bucket),
                    "tf": tf,
                    "n": n,
                    "mean_next": rn.mean(),
                    "median_next": rn.median(),
                    "p90_next": q90,
                    "p99_next": q99,
                    "|mean|_next": an.mean(),
                    "median_abs_next": an.median(),
                    "range_median_next": rnge.median(),
                })
coin_df = pd.DataFrame(coin_rows)
coin_df["ord"] = coin_df.apply(
    lambda r: FEAT_ORDER[r["feature"]].index(r["bucket"])
    if r["bucket"] in FEAT_ORDER[r["feature"]] else 999, axis=1)
coin_df = coin_df.sort_values(["feature", "tf", "coin", "ord"]).drop(columns=["ord"])
coin_df.to_csv(OUT_COIN, index=False)
print("coin rows:", len(coin_df))

print("=== STEP 7/7: per-coin replication rates ===")
POOLED = patterns.set_index(["feature", "tf", "bucket"])

def bucket_metric(pdf, coin, feat, tf, bucket, metric):
    row = pdf[(pdf["coin"] == coin) & (pdf["feature"] == feat) & (pdf["tf"] == tf) & (pdf["bucket"] == bucket)]
    if row.empty:
        return np.nan
    return float(row[metric].iloc[0])

def coin_value(pdf, coin, feat, tf, metric, group):
    vals = [bucket_metric(pdf, coin, feat, tf, b, metric) for b in group]
    vals = [v for v in vals if v is not None and not np.isnan(v)]
    if not vals:
        return np.nan
    return float(np.median(vals))

EFFECTS = [
    ("hour", "5m", "vol", "median_abs_next", "US-open (12-16) vs Asian trough (5-9)",
     ["12", "13", "14", "15", "16"], ["5", "6", "7", "8", "9"]),
    ("hour", "1h", "vol", "median_abs_next", "US-open (12-16) vs Asian trough (5-9)",
     ["12", "13", "14", "15", "16"], ["5", "6", "7", "8", "9"]),
    ("weekday", "1d", "dir", "median_next", "Mon/Tue/Wed/Sat vs Thu/Fri/Sun",
     ["0", "1", "2", "5"], ["3", "4", "6"]),
    ("weekday", "1h", "vol", "median_abs_next", "weekdays vs weekend",
     ["0", "1", "2", "3", "4"], ["5", "6"]),
    ("dom", "1d", "dir", "median_next", "top-3 vs bottom-3 dom buckets (pooled)",
     None, None),
    ("vol_pct", "5m", "vol", "median_abs_next", ">99 vs <50", [">99"], ["<50"]),
    ("vol_pct", "1h", "vol", "median_abs_next", ">99 vs <50", [">99"], ["<50"]),
    ("vol_pct", "1d", "vol", "median_abs_next", ">99 vs <50", [">99"], ["<50"]),
    ("vol_chg", "5m", "vol", "median_abs_next", "D10 vs D1", ["D10"], ["D1"]),
    ("vol_chg", "1h", "vol", "median_abs_next", "D10 vs D1", ["D10"], ["D1"]),
    ("vol_per_move", "5m", "vol", "median_abs_next", ">99 vs <50", [">99"], ["<50"]),
    ("vol_per_move", "1h", "vol", "median_abs_next", ">99 vs <50", [">99"], ["<50"]),
    ("vol_ma20", "5m", "vol", "median_abs_next", ">4x vs <0.5x", [">4x"], ["<0.5x"]),
    ("vol_ma20", "1h", "vol", "median_abs_next", ">4x vs <0.5x", [">4x"], ["<0.5x"]),
    ("vol_ma20", "1d", "vol", "median_abs_next", ">4x vs <0.5x", [">4x"], ["<0.5x"]),
    ("body_pos", "1h", "dir", "median_next", "upper vs lower", ["upper"], ["lower"]),
    ("cooloff", "5m", "vol", "median_abs_next", "0 vs 6+", ["0"], ["6+"]),
    ("cooloff", "1h", "vol", "median_abs_next", "0 vs 6+", ["0"], ["6+"]),
]

def pooled_value(feat, tf, metric, group):
    vals = []
    for b in group:
        try:
            v = POOLED.loc[(feat, tf, b), metric]
        except KeyError:
            continue
        if not np.isnan(v):
            vals.append(float(v))
    if not vals:
        return np.nan
    return float(np.median(vals))

rep_rows = []
for feat, tf, mtype, metric, label, grpA, grpB in EFFECTS:
    if feat == "dom":
        sub = POOLED.xs((feat, tf), level=["feature", "tf"])["median_next"].dropna()
        top3 = list(sub.nlargest(3).index)
        bot3 = list(sub.nsmallest(3).index)
        grpA, grpB = top3, bot3
    pA = pooled_value(feat, tf, metric, grpA)
    pB = pooled_value(feat, tf, metric, grpB)
    if np.isnan(pA) or np.isnan(pB):
        continue
    pooled_eff = pA - pB
    signs = []
    effs = {}
    for coin in sorted(coin_df["coin"].unique()):
        a = coin_value(coin_df, coin, feat, tf, metric, grpA)
        b = coin_value(coin_df, coin, feat, tf, metric, grpB)
        if np.isnan(a) or np.isnan(b):
            continue
        eff = a - b
        effs[coin] = eff
        if abs(eff) > 1e-12:
            signs.append(1 if eff > 0 else -1)
    pool_sign = 1 if pooled_eff > 0 else (-1 if pooled_eff < 0 else 0)
    if pool_sign == 0 or not signs:
        continue
    matches = sum(1 for s in signs if s == pool_sign)
    exceptions = [c for c, e in effs.items() if abs(e) > 1e-12 and ((e > 0) != (pool_sign > 0))]
    rep_rows.append({
        "feature": feat, "tf": tf, "metric": metric, "effect": label,
        "pooled_effect": pooled_eff, "pooled_sign": pool_sign,
        "n_coins": len(signs), "matches": matches,
        "rate": matches / len(signs), "exceptions": ";".join(exceptions),
        "per_coin_effects": ";".join(f"{c}:{effs[c]:.4f}" for c in sorted(effs)),
    })
rep_df = pd.DataFrame(rep_rows)
rep_df.to_csv(OUT_REP, index=False)
print("replication rows:", len(rep_df))

print("=== STEP 8/8: hour_x_weekday heatmap data ===")
heat_rows = []
for tf in ["5m", "1h"]:
    sub = df[df["tf"] == tf]
    vol_med = sub.groupby(["weekday", "hour"], observed=True)["v"].median()
    abs_med = sub.groupby(["weekday", "hour"], observed=True)["abs_next"].median()
    for (wd, hr), v in vol_med.items():
        heat_rows.append({"tf": tf, "weekday": int(wd), "hour": int(hr), "med_vol": v, "med_absnext": abs_med[(wd, hr)]})
heat = pd.DataFrame(heat_rows)
heat.to_csv(OUT_HEAT, index=False)
print("heat rows:", len(heat))

print("=== DONE ===")
