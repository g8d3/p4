import pandas as pd
import numpy as np
from scipy import stats

IN = "../ag-01-data/output/candles_raw.csv"
OUT_EVENTS = "output/events.csv"
OUT_PATHS = "output/event_paths.csv"
OUT_EXT = "output/extension.csv"
OUT_CLUSTER = "output/clustering.csv"
OUT_SPLITS = "output/splits.csv"
OUT_MAEMFE = "output/mae_mfe.csv"
OUT_REP = "output/replication.csv"

N = 5          # pivot window
PIV_CONF = N   # confirmation lag
HORIZONS = [1, 3, 5, 10]
PATH_MAX = 10
MIN_SUBGROUP = 50

print("=== STEP 1/6: load ===")
df = pd.read_csv(IN)
df = df[df["v"] > 0]
df = df.sort_values(["coin", "tf", "t_ms"]).reset_index(drop=True)
print("rows after v>0:", len(df))

print("=== STEP 2/6: derived columns ===")
g = df.groupby(["coin", "tf"], sort=False)
df["ret"] = g["c"].pct_change() * 100.0
df["range"] = (df["h"] - df["l"]) / df["l"] * 100.0
hl = df["h"] - df["l"]
df["body"] = np.where(hl > 0, (df["c"] - df["l"]) / np.where(hl > 0, hl, np.nan), np.nan)
df["sigma"] = g["ret"].transform(lambda x: x.std(ddof=1))
rol = df.groupby(["coin", "tf"], sort=False)["ret"].rolling(20, min_periods=20).std(ddof=1)
df["rolsig"] = rol.reset_index(level=[0, 1], drop=True)
cnt = df.groupby(["coin", "tf"], sort=False).cumcount()
df["rolsig"] = df["rolsig"].where(cnt >= 50)
df["vol_pct"] = g["v"].transform(lambda s: s.rank(pct=True) * 100.0)
dt = pd.to_datetime(df["t_ms"], unit="ms", utc=True)
df["hour"] = dt.dt.hour.astype(int)
df["t"] = np.arange(len(df))

med_t = df.groupby(["coin", "tf"])["t_ms"].transform("median")
df["half"] = np.where(df["t_ms"] <= med_t, "h1", "h2")
df["rolsig_med"] = g["rolsig"].transform(lambda s: s.median())

print("=== STEP 3/6: confirmed pivots + swing distance (no lookahead) ===")
res = []
for (coin, tf), sub in df.groupby(["coin", "tf"], sort=False):
    idx = sub.index
    n = len(sub)
    h = sub["h"].values
    l = sub["l"].values
    c = sub["c"].values
    rolsig = sub["rolsig"].values
    out = pd.DataFrame(index=idx)

    is_ph = np.zeros(n, dtype=bool)
    is_pl = np.zeros(n, dtype=bool)
    for i in range(N, n - N):
        if h[i] > h[i - N:i].max() and h[i] > h[i + 1:i + N + 1].max():
            is_ph[i] = True
        if l[i] < l[i - N:i].min() and l[i] < l[i + 1:i + N + 1].min():
            is_pl[i] = True

    ph_val = np.where(is_ph, h, np.nan)
    pl_val = np.where(is_pl, l, np.nan)
    last_ph = pd.Series(ph_val, index=idx).shift(PIV_CONF).ffill()
    last_pl = pd.Series(pl_val, index=idx).shift(PIV_CONF).ffill()
    out["last_piv_high"] = last_ph.values
    out["last_piv_low"] = last_pl.values
    out["dist_high"] = np.where(np.isnan(last_ph.values), np.nan, (c - last_ph.values) / rolsig)
    out["dist_low"] = np.where(np.isnan(last_pl.values), np.nan, (c - last_pl.values) / rolsig)
    res.append(out)

dist = pd.concat(res).sort_index()
for col in ["last_piv_high", "last_piv_low", "dist_high", "dist_low"]:
    df[col] = dist[col]
# raw dist is unbounded when rolsig -> 0; clip for reporting/bucketing.
# The ext/mid/con buckets only depend on the +/-1 boundary, so clipping at
# +/-20 never changes a bucket label.
df["dist_high"] = df["dist_high"].clip(-20, 20)
df["dist_low"] = df["dist_low"].clip(-20, 20)
print("pivots defined frac:", df["dist_high"].notna().mean().round(3))

print("=== STEP 4/6: events + outcomes ===")
df["is_event"] = df["ret"].abs() > 3.0 * df["sigma"]
df["side"] = np.where(df["ret"] > 0, "up", "down")

g = df.groupby(["coin", "tf"], sort=False)
for k in range(1, PATH_MAX + 1):
    df[f"ret_k{k}"] = g["c"].shift(-k)
for k in [1, 3, 5, 10]:
    df[f"cum{k}"] = (df[f"ret_k{k}"] - df["c"]) / df["c"] * 100.0
for k in range(1, PATH_MAX + 1):
    df[f"cum_{k}"] = (df[f"ret_k{k}"] - df["c"]) / df["c"] * 100.0

low_k = {k: g["l"].shift(-k) for k in range(1, PATH_MAX + 1)}
high_k = {k: g["h"].shift(-k) for k in range(1, PATH_MAX + 1)}
mae_cols = []
mfe_cols = []
for k in range(1, PATH_MAX + 1):
    c = f"mae_k{k}"
    f = f"mfe_k{k}"
    df[c] = (low_k[k] - df["c"]) / df["c"] * 100.0
    df[f] = (high_k[k] - df["c"]) / df["c"] * 100.0
    mae_cols.append(c)
    mfe_cols.append(f)
df["mae10"] = df[mae_cols].min(axis=1)
df["mfe10"] = df[mfe_cols].max(axis=1)

ev = df[df["is_event"]].copy()
ev["ext_bucket"] = np.where(
    (ev["side"] == "up") & (ev["dist_high"] >= 1.0), "ext",
    np.where((ev["side"] == "up") & (ev["dist_high"] <= -1.0), "con",
             np.where((ev["side"] == "down") & (ev["dist_low"] <= -1.0), "ext",
                      np.where((ev["side"] == "down") & (ev["dist_low"] >= 1.0), "con", "mid"))))
ev["vol_bucket"] = np.where(ev["vol_pct"] >= 90.0, "high_vol", "low_vol")
ev["regime_bucket"] = np.where(ev["rolsig"] >= ev["rolsig_med"], "high_regime", "low_regime")
ev["hour_block"] = pd.cut(ev["hour"], [0, 6, 12, 18, 24], labels=["0-5", "6-11", "12-17", "18-23"], include_lowest=True)

ev_cols = ["coin", "tf", "t_ms", "t", "side", "ret", "sigma", "rolsig", "vol_pct", "hour", "half",
           "dist_high", "dist_low", "last_piv_high", "last_piv_low",
           "ext_bucket", "vol_bucket", "regime_bucket", "hour_block"]
for k in [1, 3, 5, 10]:
    ev_cols.append(f"cum{k}")
for k in range(1, PATH_MAX + 1):
    ev_cols.append(f"cum_{k}")
ev_cols += ["mae10", "mfe10"]
events = ev[ev_cols].copy()
events = events.sort_values(["tf", "coin", "t_ms"]).reset_index(drop=True)
events.to_csv(OUT_EVENTS, index=False)
print("events:", len(events))

print("=== STEP 5/6: paths, splits, extension, clustering, MAE/MFE ===")

path_rows = []
for (side, tf, half), grp in events.groupby(["side", "tf", "half"]):
    n = len(grp)
    for k in range(1, PATH_MAX + 1):
        col = f"cum_{k}"
        vals = grp[col].dropna()
        path_rows.append({"side": side, "tf": tf, "half": half, "n": n, "k": k,
                          "mean_cum": vals.mean(), "median_cum": vals.median()})
for (side, tf), grp in events.groupby(["side", "tf"]):
    n = len(grp)
    for k in range(1, PATH_MAX + 1):
        col = f"cum_{k}"
        vals = grp[col].dropna()
        path_rows.append({"side": side, "tf": tf, "half": "all", "n": n, "k": k,
                          "mean_cum": vals.mean(), "median_cum": vals.median()})
paths = pd.DataFrame(path_rows)
paths.to_csv(OUT_PATHS, index=False)
print("paths rows:", len(paths))

split_rows = []
for (side, tf), grp in events.groupby(["side", "tf"]):
    c5 = grp["cum5"].dropna()
    base = {"side": side, "tf": tf, "n": len(c5), "mean5": c5.mean(), "median5": c5.median(),
            "p25": c5.quantile(0.25), "p75": c5.quantile(0.75)}
    base.update({f"{key}_n": 0 for key in ["ext", "con", "mid"]})
    split_rows.append(base)
    for split, col, ordered in [("ext", "ext_bucket", ["ext", "mid", "con"]),
                                ("vol", "vol_bucket", ["high_vol", "low_vol"]),
                                ("regime", "regime_bucket", ["high_regime", "low_regime"]),
                                ("hour", "hour_block", ["0-5", "6-11", "12-17", "18-23"])]:
        for bucket in ordered:
            sub = grp[grp[col] == bucket]
            v = sub["cum5"].dropna()
            split_rows.append({"side": side, "tf": tf, "split": split, "bucket": str(bucket),
                               "n": len(v), "mean5": v.mean() if len(v) else np.nan,
                               "median5": v.median() if len(v) else np.nan,
                               "p25": v.quantile(0.25) if len(v) else np.nan,
                               "p75": v.quantile(0.75) if len(v) else np.nan,
                               "h1_mean5": sub.loc[sub["half"] == "h1", "cum5"].mean() if (sub["half"] == "h1").any() else np.nan,
                               "h2_mean5": sub.loc[sub["half"] == "h2", "cum5"].mean() if (sub["half"] == "h2").any() else np.nan,
                               "h1_n": (sub["half"] == "h1").sum(), "h2_n": (sub["half"] == "h2").sum()})
splits = pd.DataFrame(split_rows)
splits.to_csv(OUT_SPLITS, index=False)
print("splits rows:", len(splits))

ext_rows = []
for (side, tf), grp in events.groupby(["side", "tf"]):
    for bucket in ["ext", "mid", "con"]:
        sub = grp[grp["ext_bucket"] == bucket]
        v = sub["cum5"].dropna()
        ext_rows.append({"side": side, "tf": tf, "ext_bucket": bucket, "n": len(v),
                         "mean5": v.mean() if len(v) else np.nan, "median5": v.median() if len(v) else np.nan})
ext = pd.DataFrame(ext_rows)
ext.to_csv("output/splits_ext.csv", index=False)

# extension distribution on all candles + event-rate conditioning
ext2_rows = []
for tf in sorted(df["tf"].unique()):
    sub = df[df["tf"] == tf]
    for col in ["dist_high", "dist_low"]:
        v = sub[col].dropna()
        ext2_rows.append({"tf": tf, "col": col, "n": len(v), "p50": v.quantile(0.5),
                          "p90": v.quantile(0.9), "p99": v.quantile(0.99),
                          "mean": v.mean(), "frac_abs_ge1": (v.abs() >= 1).mean()})
    for cond in ["ext_up", "ext_down"]:
        if cond == "ext_up":
            mask = sub["dist_high"] >= 1.0
            ev_mask = sub["is_event"] & (sub["ret"] > 0)
        else:
            mask = sub["dist_low"] <= -1.0
            ev_mask = sub["is_event"] & (sub["ret"] < 0)
        known = mask.notna() if mask.dtype == object else mask
        n_ext = int(mask.sum())
        if n_ext == 0:
            continue
        rate_ext = ev_mask[mask].sum() / n_ext * 1000.0
        n_not = int((~mask).sum())
        rate_not = ev_mask[~mask].sum() / n_not * 1000.0 if n_not else np.nan
        ext2_rows.append({"tf": tf, "col": cond, "n": n_ext, "rate_per_1k": rate_ext,
                          "rate_not_per_1k": rate_not,
                          "ratio": rate_ext / rate_not if rate_not and rate_not > 0 else np.nan})
ext2 = pd.DataFrame(ext2_rows)
ext2.to_csv(OUT_EXT, index=False)
print("extension rows:", len(ext2))

ctx_rows = []
for tf in sorted(df["tf"].unique()):
    sub = df[df["tf"] == tf]
    base5 = sub["cum5"].dropna()
    ctx_rows.append({"tf": tf, "scope": "all", "side": "all", "n": len(base5),
                     "mean5": base5.mean(), "median5": base5.median()})
    for side in ["up", "down"]:
        m = sub[sub["side"] == side]["cum5"].dropna()
        me = ev[(ev["tf"] == tf) & (ev["side"] == side)]["cum5"].dropna()
        er = ev[(ev["tf"] == tf) & (ev["side"] == side)]["ret"].abs()
        ctx_rows.append({"tf": tf, "scope": "all_" + side, "side": side, "n": len(m),
                         "mean5": m.mean(), "median5": m.median()})
        ctx_rows.append({"tf": tf, "scope": "events", "side": side, "n": len(me),
                         "mean5": me.mean(), "median5": me.median(),
                         "event_|ret|_mean": er.mean(), "event_|ret|_median": er.median()})
ctx = pd.DataFrame(ctx_rows)
ctx.to_csv("output/context.csv", index=False)
print("context rows:", len(ctx))

cluster_rows = []
for (coin, tf), grp in events.groupby(["coin", "tf"]):
    n_ev = len(grp)
    n_cand = (df["coin"] == coin) & (df["tf"] == tf)
    total = int(n_cand.sum())
    if n_ev < 2:
        continue
    idx = grp["t"].values
    intervals = np.diff(idx)
    p = n_ev / total
    cluster_rows.append({"coin": coin, "tf": tf, "n_events": n_ev, "n_candles": total,
                         "p": p, "mean_int": intervals.mean(), "exp_mean": 1.0 / p,
                         "ratio": intervals.mean() * p,
                         "median_int": np.median(intervals),
                         "frac_le10": (intervals <= 10).mean(),
                         "exp_frac_le10": 1 - (1 - p) ** 10,
                         "cv2": intervals.var() / (intervals.mean() ** 2)})
cluster = pd.DataFrame(cluster_rows)
cluster.to_csv(OUT_CLUSTER, index=False)
print("cluster rows:", len(cluster))

mae_rows = []
for (side, tf), grp in events.groupby(["side", "tf"]):
    mae = grp["mae10"].dropna()
    mfe = grp["mfe10"].dropna()
    mae_rows.append({"side": side, "tf": tf, "n": len(mae),
                     "mae_med": mae.median(), "mae_p90": mae.quantile(0.9), "mae_min": mae.min(),
                     "mfe_med": mfe.median(), "mfe_p90": mfe.quantile(0.9), "mfe_max": mfe.max(),
                     "mae_ratio": (mae / mfe.abs()).median()})
mae_df = pd.DataFrame(mae_rows)
mae_df.to_csv(OUT_MAEMFE, index=False)
print("mae/mfe rows:", len(mae_df))

print("=== STEP 6/6: per-coin replication ===")
rep_rows = []
for (side, tf), grp in events.groupby(["side", "tf"]):
    per_coin = {}
    for coin, cg in grp.groupby("coin"):
        v = cg["cum5"].dropna()
        if len(v) >= 5:
            per_coin[coin] = v.mean()
    all_mean = grp["cum5"].dropna().mean()
    if not per_coin:
        continue
    n_pos = sum(1 for x in per_coin.values() if x > 0)
    h1 = grp[grp["half"] == "h1"]["cum5"].dropna()
    h2 = grp[grp["half"] == "h2"]["cum5"].dropna()
    rep_rows.append({"side": side, "tf": tf, "pooled_n": len(grp), "pooled_mean5": all_mean,
                     "n_coins": len(per_coin), "n_positive": n_pos,
                     "rate_same_sign": n_pos / len(per_coin),
                     "h1_n": len(h1), "h2_n": len(h2),
                     "h1_mean5": h1.mean(), "h2_mean5": h2.mean(),
                     "half_replicated": bool(np.sign(h1.mean()) == np.sign(h2.mean())),
                     "coins": ";".join(f"{c}:{v:.3f}" for c, v in sorted(per_coin.items()))})
rep = pd.DataFrame(rep_rows)
rep.to_csv(OUT_REP, index=False)
print("rep rows:", len(rep))

# keep a plain-events-per-tf summary for the report
summ = events.groupby(["tf", "side"]).size().to_frame("n").reset_index()
print(summ.to_string(index=False))

print("=== DONE ===")
