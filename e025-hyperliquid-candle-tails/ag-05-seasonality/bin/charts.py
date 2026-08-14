import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

pd.set_option("display.float_format", lambda x: f"{x:.4f}")

IN = "../ag-01-data/output/candles_raw.csv"
PATTERNS = "output/patterns.csv"
HEAT = "output/heatmap_data.csv"
CHART_DIR = "output/charts"

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
FEAT_LABEL = {
    "hour": "hour (UTC, candle open)",
    "weekday": "weekday (Mon=0..Sun=6)",
    "dom": "day of month",
    "vol_pct": "volume percentile within (coin,tf)",
    "vol_chg": "volume change decile within (coin,tf)",
    "vol_per_move": "volume per unit move, percentile",
    "vol_ma20": "v vs trailing 20-period median volume",
    "body_pos": "body position in range",
    "cooloff": "periods since |ret| >= 2 sigma",
}

print("=== compute derived columns for error bars ===")
df = pd.read_csv(IN)
df = df[df["v"] > 0].sort_values(["coin", "tf", "t_ms"]).reset_index(drop=True)
g = df.groupby(["coin", "tf"], sort=False)
df["ret"] = g["c"].pct_change() * 100.0
df["range"] = (df["h"] - df["l"]) / df["l"] * 100.0
hl = df["h"] - df["l"]
df["body"] = np.where(hl > 0, (df["c"] - df["l"]) / np.where(hl > 0, hl, np.nan), np.nan)
df["sig"] = g["ret"].transform(lambda x: x.std(ddof=1))
df["big"] = df["ret"].abs() >= 2.0 * df["sig"]
df["vol_chg"] = g["v"].pct_change()
df["vol_per_move"] = np.where(df["ret"].abs() > 1e-9, df["v"] / df["ret"].abs(), np.nan)
df["v_prev"] = g["v"].shift(1)
ma20 = df.groupby(["coin", "tf"], sort=False)["v_prev"].rolling(20, min_periods=5).median()
df["vol_ma20"] = df["v"] / ma20.reset_index(level=[0, 1], drop=True)

dt = pd.to_datetime(df["t_ms"], unit="ms", utc=True)
df["hour"] = dt.dt.hour.astype(int).astype(str)
df["weekday"] = dt.dt.weekday.astype(int).astype(str)
df["dom"] = dt.dt.day.astype(int).astype(str)

def pct_bucket(s):
    r = s.rank(pct=True, method="average")
    return pd.cut(r, [-0.001, 0.5, 0.9, 0.99, 1.001], labels=["<50", "50-90", "90-99", ">99"]).astype(str)

df["vol_pct"] = g["v"].transform(pct_bucket)
df["vol_per_move_b"] = g["vol_per_move"].transform(pct_bucket)
df["vol_chg_b"] = g["vol_chg"].transform(lambda s: pd.qcut(s.rank(method="first"), 10, labels=["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10"])).astype(str)
df["vol_ma20_b"] = pd.cut(df["vol_ma20"], [-np.inf, 0.5, 1.0, 2.0, 4.0, np.inf], labels=["<0.5x", "0.5-1x", "1-2x", "2-4x", ">4x"]).astype(str)
df["body_b"] = pd.cut(df["body"], [-np.inf, 0.15, 0.85, np.inf], labels=["lower", "mid", "upper"]).astype(str)
grpbig = df["big"].cumsum()
cnt = grpbig.groupby(grpbig).cumcount()
df["cooloff_b"] = np.select(
    [grpbig == 0, cnt == 0, cnt <= 2, cnt <= 5],
    ["never", "0", "1-2", "3-5"],
    default="6+",
).astype(str)

df["ret_next"] = g["ret"].shift(-1)
df["abs_next"] = df["ret_next"].abs()
df = df[df["ret_next"].notna()]

FEAT_COL = {
    "hour": "hour", "weekday": "weekday", "dom": "dom", "vol_pct": "vol_pct",
    "vol_chg": "vol_chg_b", "vol_per_move": "vol_per_move_b",
    "vol_ma20": "vol_ma20_b", "body_pos": "body_b", "cooloff": "cooloff_b",
}

patterns = pd.read_csv(PATTERNS)
tfs = sorted(df["tf"].unique())

def se_median(values):
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) < 2:
        return 0.0
    q1, q3 = np.percentile(values, [25, 75])
    return 1.58 * (q3 - q1) / np.sqrt(len(values))

print("=== bar charts ===")
made = 0
for feat, col in FEAT_COL.items():
    for tf in tfs:
        sub = df[df["tf"] == tf]
        p = patterns[(patterns["feature"] == feat) & (patterns["tf"] == tf)]
        if p.empty:
            continue
        keep = p[p["n"] >= 30]
        if len(keep) < 3:
            print(f"skip {feat} {tf}: only {len(p)} buckets")
            continue
        order = [b for b in FEAT_ORDER[feat] if b in set(keep["bucket"])]
        p = keep.set_index("bucket").reindex(order).dropna(subset=["median_next"])
        if len(p) < 3:
            continue
        med_next = p["median_next"].values
        abs_next = p["median_abs_next"].values
        err_d = []
        err_v = []
        for b in p.index:
            vals_d = sub.loc[sub[col] == b, "ret_next"]
            vals_a = sub.loc[sub[col] == b, "abs_next"]
            err_d.append(se_median(vals_d))
            err_v.append(se_median(vals_a))
        overall_d = sub["ret_next"].median()
        overall_v = sub["abs_next"].median()

        fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
        x = np.arange(len(p))
        axes[0].bar(x, med_next, color="#4c72b0", yerr=err_d, capsize=3, error_kw={"lw": 0.8})
        axes[0].axhline(overall_d, color="red", lw=1, ls="--")
        axes[0].set_title(f"{feat} · {tf} — median ret_next (dir)")
        axes[0].set_xlabel(FEAT_LABEL[feat])
        axes[0].set_ylabel("%")
        axes[0].set_xticks(x)
        axes[0].tick_params(axis="x", rotation=90)
        axes[0].set_xticklabels(p.index)

        axes[1].bar(x, abs_next, color="#c44e52", yerr=err_v, capsize=3, error_kw={"lw": 0.8})
        axes[1].axhline(overall_v, color="red", lw=1, ls="--")
        axes[1].set_title(f"{feat} · {tf} — median |ret_next| (vol)")
        axes[1].set_xlabel(FEAT_LABEL[feat])
        axes[1].set_ylabel("%")
        axes[1].set_xticks(x)
        axes[1].tick_params(axis="x", rotation=90)
        axes[1].set_xticklabels(p.index)
        fig.suptitle(f"{feat} — {tf}  (red = overall median)")
        fig.tight_layout()
        out = f"{CHART_DIR}/{feat}_{tf}.png"
        fig.savefig(out, dpi=110)
        plt.close(fig)
        made += 1
print("bar charts made:", made)

print("=== heatmaps ===")
heat = pd.read_csv(HEAT)
WD = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
for tf in sorted(heat["tf"].unique()):
    h = heat[heat["tf"] == tf]
    vp = h.pivot(index="weekday", columns="hour", values="med_vol").reindex(range(7)).sort_index()
    ap = h.pivot(index="weekday", columns="hour", values="med_absnext").reindex(range(7)).sort_index()
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.0))
    for ax, mat, title, cmap in [(axes[0], np.log10(vp.values), "median volume (log10)", "viridis"),
                                 (axes[1], ap.values, "median |ret_next| %", "magma")]:
        im = ax.imshow(mat, aspect="auto", cmap=cmap)
        ax.set_yticks(range(7))
        ax.set_yticklabels(WD)
        ax.set_xticks(range(0, 24, 2))
        ax.set_xticklabels(range(0, 24, 2))
        ax.set_xlabel("hour UTC")
        ax.set_title(title)
        fig.colorbar(im, ax=ax, shrink=0.8)
    fig.suptitle(f"hour_x_weekday heatmap — {tf}")
    fig.tight_layout()
    out = f"{CHART_DIR}/hour_x_weekday_{tf}.png"
    fig.savefig(out, dpi=110)
    plt.close(fig)
print("=== DONE ===")
