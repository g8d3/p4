import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CH = "output/charts"
EVENTS = "output/events.csv"
PATHS = "output/event_paths.csv"
EXT = "output/extension.csv"
MAEMFE = "output/mae_mfe.csv"
SPLITS = "output/splits.csv"

COL = {"up": "#2ca02c", "down": "#d62728"}
ORDER = ["5m", "1h", "1d"]
LBL = {"5m": "5m", "1h": "1h", "1d": "1d"}

ev = pd.read_csv(EVENTS)
paths = pd.read_csv(PATHS)
ext = pd.read_csv(EXT)
mae_df = pd.read_csv(MAEMFE)
splits = pd.read_csv(SPLITS)

def add_base(ax):
    ax.axhline(0, color="0.5", lw=0.8)

print("=== chart 1-3: path curves ===")
for tf in ["5m", "1h", "1d"]:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for side, c in COL.items():
        p = paths[(paths["tf"] == tf) & (paths["side"] == side) & (paths["half"] == "all")].sort_values("k")
        ax.plot(p["k"], p["mean_cum"], c=c, ls="-", lw=2, label=f"{side} mean (n={int(p['n'].iloc[0])})")
        ax.plot(p["k"], p["median_cum"], c=c, ls="--", lw=1.5, label=f"{side} median")
    add_base(ax)
    ax.set_title(f"{tf}: mean & median cumulative return after 3σ events (candles 1..10)")
    ax.set_xlabel("candles after event close")
    ax.set_ylabel("cumulative return (%)")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(alpha=0.3, lw=0.5)
    fig.tight_layout()
    fig.savefig(f"{CH}/paths_{tf}.png", dpi=130)
    plt.close(fig)

print("=== chart 4: MAE / MFE ===")
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
groups = [(s, t) for t in ORDER for s in ["up", "down"]]
pos = np.arange(len(groups))
w = 0.38
for ax, metric, title in [(axes[0], "mae_med", "max adverse excursion (median, %)"),
                          (axes[1], "mfe_med", "max favorable excursion (median, %)")]:
    vals = [mae_df[(mae_df["side"] == s) & (mae_df["tf"] == t)][metric].iloc[0] for s, t in groups]
    bars = ax.bar(pos, vals, color=[COL[s] for s, _ in groups], width=0.6)
    ax.set_xticks(pos)
    ax.set_xticklabels([f"{s[0]}{t}" for s, t in groups], fontsize=9)
    ax.set_title(f"{title}  (next 10 candles)")
    ax.grid(alpha=0.3, axis="y", lw=0.5)
    ax.axhline(0, color="0.4", lw=0.8)
    for b, v in zip(bars, vals):
        ax.annotate(f"{v:.2f}", (b.get_x() + b.get_width() / 2, v), ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=8)
fig.tight_layout()
fig.savefig(f"{CH}/mae_mfe.png", dpi=130)
plt.close(fig)

print("=== chart 5: event intervals vs geometric expectation ===")
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
for ax, tf in zip(axes, ["5m", "1h"]):
    sub = ev[ev["tf"] == tf].sort_values(["coin", "t"])
    intervals = sub.groupby("coin")["t"].diff().dropna().values
    p = len(ev[ev["tf"] == tf]) / max(1, len(sub) + intervals.sum() + 1)
    ax.hist(intervals, bins=np.arange(0, max(intervals.max(), 20) + 1, 1), color="0.6", alpha=0.7, label="observed")
    xs = np.arange(1, 101)
    expect = (1 - p) ** (xs - 1) * p * len(intervals)
    ax.plot(xs, expect, c="crimson", lw=2, label=f"geometric(p={p:.3f})")
    ax.set_title(f"{tf}: candles until next event (per coin)")
    ax.set_xlim(0, min(60, max(intervals.max(), 20)))
    ax.set_xlabel("candles between consecutive events")
    ax.set_ylabel("count")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(alpha=0.3, lw=0.5)
fig.tight_layout()
fig.savefig(f"{CH}/intervals.png", dpi=130)
plt.close(fig)

print("=== chart 6: extension x reaction ===")
fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
for ax, tf in zip(axes, ORDER):
    xs = np.array([0, 0.45, 0.9])
    for si, side in enumerate(["up", "down"]):
        rows = splits[(splits["tf"] == tf) & (splits["side"] == side) & (splits["split"] == "ext")].set_index("bucket")
        for bi, bucket in enumerate(["ext", "mid", "con"]):
            if bucket in rows.index and pd.notna(rows.loc[bucket, "mean5"]):
                ax.bar(xs[bi] + si * 0.13, rows.loc[bucket, "mean5"], width=0.12,
                       color=COL[side], alpha=0.55 + 0.15 * bi,
                       label=(f"{side} {bucket}" if si == 0 and bi == 0 else None))
    ax.set_xticks(xs + 0.065)
    ax.set_xticklabels(["extended\n(|dist|>=1)", "mid", "contra\n(dist<=-1)"], fontsize=8)
    ax.set_title(f"{tf}: next-5 mean return by extension at event")
    ax.set_ylabel("mean cum5 (%)")
    ax.grid(alpha=0.3, axis="y", lw=0.5)
    add_base(ax)
    if tf == ORDER[-1]:
        ax.legend(frameon=False, fontsize=8, loc="upper right")
fig.tight_layout()
fig.savefig(f"{CH}/extension_reaction.png", dpi=130)
plt.close(fig)

print("=== chart 7: volume & regime splits ===")
fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
for ax, split, title in [(axes[0], "vol", "volume percentile at event (high>=p90 vs low)"),
                         (axes[1], "regime", "regime at event (rolsig >= median vs low)")]:
    xs = np.arange(len(groups))
    for si, (s, t) in enumerate(groups):
        rows = splits[(splits["tf"] == t) & (splits["side"] == s) & (splits["split"] == split)]
        buckets = rows["bucket"].tolist()
        vals = rows["mean5"].tolist()
        for bi, (b, v) in enumerate(zip(buckets, vals)):
            if pd.notna(v):
                ax.bar(xs[si] + (bi - 0.5) * 0.28, v, width=0.25, color=COL[s], alpha=0.4 + 0.3 * bi)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{s[0]}{t}" for s, t in groups], fontsize=9)
    ax.set_title(f"next-5 mean return by {title}")
    ax.grid(alpha=0.3, axis="y", lw=0.5)
    add_base(ax)
fig.tight_layout()
fig.savefig(f"{CH}/splits_vol_regime.png", dpi=130)
plt.close(fig)

print("=== chart 8: event rate when extended vs not ===")
rows = ext[ext["col"].isin(["ext_up", "ext_down"])]
fig, ax = plt.subplots(figsize=(9, 4.5))
xs = np.arange(len(rows))
for i, (_, r) in enumerate(rows.iterrows()):
    ax.bar(i, r["rate_per_1k"], color=COL["up" if "up" in r["col"] else "down"], alpha=0.85)
    ax.bar(i, r["rate_not_per_1k"], color="0.55", alpha=0.7)
ax.set_xticks(xs)
ax.set_xticklabels([f"{r['col'].replace('_',' ')} {r['tf']}" for _, r in rows.iterrows()], fontsize=9)
ax.set_ylabel("events per 1,000 candles")
ax.set_title("3σ event rate: candle already extended past last confirmed swing vs not")
ax.grid(alpha=0.3, axis="y", lw=0.5)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color="0.55", label="not extended"), Patch(color=COL["up"], label="up events"),
                   Patch(color=COL["down"], label="down events")], frameon=False, fontsize=9)
fig.tight_layout()
fig.savefig(f"{CH}/event_rate_extension.png", dpi=130)
plt.close(fig)

print("=== DONE charts ===")
