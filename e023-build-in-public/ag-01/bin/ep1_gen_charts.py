#!/usr/bin/env python3
"""E01 real-data charts for the video. Dark theme, big, readable."""
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EXP = "/home/vuos/code/p4/e022-nautilus-sr-grid/ag-01"
OUT = "/home/vuos/code/p4/e023-build-in-public/ag-01/output/slides/v3"

BG = "#0d1117"
FG = "#e6edf3"
MUT = "#8b949e"
GREEN = "#3fb950"
RED = "#f85149"
BLUE = "#58a6ff"
GOLD = "#f0c674"

def style():
    plt.rcParams.update({
        "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
        "text.color": FG, "axes.edgecolor": "#30363d", "axes.labelcolor": FG,
        "xtick.color": MUT, "ytick.color": MUT, "grid.color": "#21262d",
        "font.size": 22, "axes.titlesize": 30, "axes.labelsize": 24,
        "legend.fontsize": 20, "lines.linewidth": 3,
    })

def save(fig, name):
    fig.set_size_inches(19.2, 10.8)
    fig.tight_layout()
    fig.savefig(f"{OUT}/{name}.png", dpi=100)
    plt.close(fig)
    print(f"  {name}.png ok")

style()

# 1. Synthetic range price
df = pd.read_csv(f"{EXP}/data/synthetic_5m_range.csv", parse_dates=["timestamp"])
fig, ax = plt.subplots()
ax.plot(df["timestamp"], df["close"], color=BLUE)
ax.set_title("SYNTHETIC RANGE MARKET")
ax.set_ylabel("price (USDT)")
ax.grid(True, alpha=0.3)
save(fig, "ch_synth_range")

# 2. Synthetic mixed price
df = pd.read_csv(f"{EXP}/data/synthetic_5m_mixed.csv", parse_dates=["timestamp"])
fig, ax = plt.subplots()
ax.plot(df["timestamp"], df["close"], color=BLUE)
ax.set_title("SYNTHETIC MIXED MARKET")
ax.set_ylabel("price (USDT)")
ax.grid(True, alpha=0.3)
save(fig, "ch_synth_mixed")

# 3. Real BTC 5m (downsampled to 2% of points)
df = pd.read_csv(f"{EXP}/data/real_btc_5m.csv", parse_dates=["timestamp"])
step = max(1, len(df)//2000)
fig, ax = plt.subplots()
ax.plot(df["timestamp"][::step], df["close"][::step], color=GOLD)
ax.set_title("REAL BTC · 5m · 1 YEAR (105,122 bars)")
ax.set_ylabel("price (USDT)")
ax.grid(True, alpha=0.3)
save(fig, "ch_real_btc_5m")

# 4. Real BTC 1h
df = pd.read_csv(f"{EXP}/data/real_btc_1h.csv", parse_dates=["timestamp"])
step = max(1, len(df)//2000)
fig, ax = plt.subplots()
ax.plot(df["timestamp"][::step], df["close"][::step], color=GOLD)
ax.set_title("REAL BTC · 1h · 4 YEARS (35,065 bars)")
ax.set_ylabel("price (USDT)")
ax.grid(True, alpha=0.3)
save(fig, "ch_real_btc_1h")

# 5. v1 vs v2 equity curves (5m) — read CSVs
def equity(fn):
    p = f"{EXP}/output/{fn}/equity_curve.csv"
    try:
        df = pd.read_csv(p)
    except Exception:
        return None
    return df
eq_v1 = equity("real_robust")
eq_v2 = equity("v2_5m")
fig, ax = plt.subplots()
if eq_v1 is not None:
    cols = [c for c in eq_v1.columns if "equity" in c.lower() or "balance" in c.lower()]
    xcol = eq_v1.columns[0]
    if cols:
        ax.plot(eq_v1[xcol], eq_v1[cols[0]], color=RED, label="v1 robust")
if eq_v2 is not None:
    cols = [c for c in eq_v2.columns if "equity" in c.lower() or "balance" in c.lower()]
    xcol = eq_v2.columns[0]
    if cols:
        ax.plot(eq_v2[xcol], eq_v2[cols[0]], color=GREEN, label="v2 redesign")
ax.set_title("REAL BTC 5m · EQUITY · v1 vs v2")
ax.set_ylabel("equity (USDT)")
ax.axhline(100000, color=MUT, ls="--", alpha=0.6, label="start 100k")
ax.legend()
ax.grid(True, alpha=0.3)
save(fig, "ch_equity_v1v2_5m")

# 6. fills & fees bar comparison
import csv
rows = list(csv.DictReader(open(f"{EXP}/output/v2_final_summary.csv")))
labels = ["v1 5m", "v2 5m", "v1 1h", "v2 1h"]
fills = [int(r["n_fills"]) for r in rows if r["run"] in ("5m_v1_robust","5m_v2","1h_v1_robust","1h_v2")]
fees = [float(r["commissions"]) for r in rows if r["run"] in ("5m_v1_robust","5m_v2","1h_v1_robust","1h_v2")]
fig, axs = plt.subplots(1, 2)
axs[0].bar(labels, fills, color=[RED,GREEN,RED,GREEN])
axs[0].set_title("FILLS (lower = better)")
axs[0].tick_params(axis="x", rotation=20, labelsize=18)
axs[1].bar(labels, fees, color=[RED,GREEN,RED,GREEN])
axs[1].set_title("FEES USDT (lower = better)")
axs[1].tick_params(axis="x", rotation=20, labelsize=18)
save(fig, "ch_fills_fees")
