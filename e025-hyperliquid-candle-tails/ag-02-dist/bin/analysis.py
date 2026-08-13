import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "..", "ag-01-data", "output", "candles_raw.csv")
OUT = os.path.join(ROOT, "output")
CH = os.path.join(OUT, "charts")
os.makedirs(CH, exist_ok=True)

TFS = ["5m", "1h", "1d", "1w"]
NBINS = 60

df = pd.read_csv(SRC)
n_raw = len(df)
v0 = (df.v == 0).sum()
df = df[df.v > 0].copy()
df = df.sort_values(["coin", "tf", "t_ms"])

df["ret"] = df.groupby(["coin", "tf"]).c.pct_change() * 100.0
df["range"] = (df.h - df.l) / df.l * 100.0
df = df[df.ret.notna()].copy()
n_ret = len(df)

stats_rows = []
for (coin, tf), g in df.groupby(["coin", "tf"]):
    r = g["ret"].dropna()
    stats_rows.append({
        "coin": coin, "tf": tf, "n": len(r),
        "mean": r.mean(), "stdev": r.std(ddof=1),
        "skew": r.skew(), "kurtosis": r.kurt() + 3.0,
        "p50": r.quantile(0.50), "p90": r.quantile(0.90),
        "p99": r.quantile(0.99), "p99_9": r.quantile(0.999),
        "min": r.min(), "max": r.max(),
    })
stats = pd.DataFrame(stats_rows)
stats = stats.sort_values(["tf", "coin"]).reset_index(drop=True)
stats.to_csv(os.path.join(OUT, "stats.csv"), index=False)

def zscore(x):
    return (x - x.mean()) / x.std(ddof=1)

df["z"] = df.groupby(["coin", "tf"]).ret.transform(zscore)

# ---- histograms: pooled across coins, per tf, ~60 equal-width bins centered on 0 ----
for tf in TFS:
    r = df[df.tf == tf].ret.values
    mx = max(abs(r.min()), abs(r.max()))
    edges = np.linspace(-mx, mx, NBINS + 1)
    counts, _ = np.histogram(r, bins=edges)
    mid = (edges[:-1] + edges[1:]) / 2
    h = pd.DataFrame({"bucket_low": edges[:-1], "bucket_high": edges[1:], "count": counts})
    h.to_csv(os.path.join(OUT, f"hist_{tf}.csv"), index=False)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(mid, counts, width=edges[1] - edges[0], color="#1f77b4", edgecolor="black", linewidth=0.3)
    ax.set_yscale("log")
    ax.set_title(f"{tf} — pooled returns across coins (n={len(r):,})")
    ax.set_xlabel("ret (%)")
    ax.set_ylabel("count (log)")
    ax.axvline(0, color="red", linewidth=0.8, linestyle="--")
    fig.tight_layout()
    fig.savefig(os.path.join(CH, f"hist_{tf}.png"), dpi=140)
    plt.close(fig)

# ---- overlay: tail heaviness across tf, z-scored per (coin, tf) ----
fig, ax = plt.subplots(figsize=(10, 5))
colors = {"5m": "#1f77b4", "1h": "#ff7f0e", "1d": "#2ca02c", "1w": "#d62728"}
for tf in TFS:
    z = df[df.tf == tf].z.values
    lo, hi = np.percentile(z, [0.1, 99.9])
    lo = min(lo, -6.0)
    hi = max(hi, 6.0)
    edges = np.linspace(lo, hi, 81)
    counts, _ = np.histogram(z, bins=edges)
    mid = (edges[:-1] + edges[1:]) / 2
    ax.plot(mid, counts, label=tf, color=colors[tf], linewidth=1.6)
ax.set_yscale("log")
ax.set_xlabel("z-score (per coin,tf)")
ax.set_ylabel("count (log)")
ax.set_title("Tail heaviness across timeframes — z-scored returns, log-y")
ax.legend(title="tf")
ax.axvline(0, color="gray", linewidth=0.8, linestyle="--")
fig.tight_layout()
fig.savefig(os.path.join(CH, "overlay_tails.png"), dpi=140)
plt.close(fig)

# ---- unconditional stats per tf (pooled across coins) for the report ----
rows = []
for tf in TFS:
    z = df[df.tf == tf].z.values
    rows.append({
        "tf": tf, "n": int(len(z)),
        "kurtosis_unconditional": float(pd.Series(z).kurt() + 3.0),
        "p99_9_in_sigma": float(np.quantile(z, 0.999)),
        "p99_9_in_pct": float(df[df.tf == tf].ret.quantile(0.999)),
    })
uncond = pd.DataFrame(rows)

with open(os.path.join(OUT, "report.md"), "w") as f:
    f.write("# ag-02 distribution report\n\n")
    f.write(f"Input: `../ag-01-data/output/candles_raw.csv` ({n_raw:,} raw rows).\n")
    f.write(f"Rows dropped: {v0:,} synthetic pre-listing candles (v=0). Returns computed on {n_ret:,} rows.\n\n")
    f.write("## Unconditional (pooled across coins, per tf)\n\n")
    f.write(uncond.to_markdown(index=False))
    f.write("\n\nKurtosis is raw (Pearson) kurtosis — normal = 3. p99.9 in σ units: for a normal "
            "distribution this is ~3.09σ.\n\n")
    f.write("## Per coin, per tf (from stats.csv)\n\n")
    f.write("Fat-tail criterion: kurtosis > 3 and p99.9 beyond ±4σ.\n\n")
    for tf in TFS:
        s = stats[stats.tf == tf]
        k = s.sort_values("kurtosis", ascending=False)
        f.write(f"### {tf}\n\n")
        f.write("Top 3 kurtosis: " + ", ".join(
            f"{c['coin']}={c['kurtosis']:.2f}" for _, c in k.head(3).iterrows()) + "\n")
        worst = s.loc[s["p99_9"].abs().idxmax()]
        f.write(f"Most extreme p99.9: {worst['coin']} p99.9={worst['p99_9']:.2f}%, "
                f"min={worst['min']:.2f}%, max={worst['max']:.2f}%\n\n")

print("=== done ===")
print("rows raw", n_raw, "v0 dropped", v0, "rows with ret", n_ret)
print(stats.head().to_string())
print()
print(uncond.to_string())
