#!/usr/bin/env python3
"""ag-08 — equity curve chart: Rule A vs B vs C, net of taker fees."""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

eq = pd.read_csv("output/equity_daily.csv", index_col=0)
eq.index = pd.to_datetime(eq.index)

styles = {
    "A (crash, hold 5)": dict(color="#2e7d32", lw=2.2, ls="-"),
    "B (rally, hold 5)": dict(color="#c62828", lw=2.2, ls="-"),
    "C (always long)": dict(color="#555555", lw=2.2, ls="--"),
    "A sens. hold 3": dict(color="#66bb6a", lw=1.2, ls=":"),
    "A sens. hold 10": dict(color="#388e3c", lw=1.2, ls=":"),
}
main = ["A (crash, hold 5)", "B (rally, hold 5)", "C (always long)"]
sens = ["A sens. hold 3", "A sens. hold 10"]

fig, ax = plt.subplots(figsize=(11, 6.5))
for name in main:
    ax.plot(eq.index, eq[name] * 100, label=name, **styles[name])
for name in sens:
    ax.plot(eq.index, eq[name] * 100, label=name, alpha=0.8, **styles[name])

ax.axhline(100, color="grey", lw=0.8)
ax.set_yscale("log")
ax.set_title("ag-08 — Out-of-sample equity, net of taker fees (pooled equal weight per day)")
ax.set_ylabel("Equity index (start = 100, log scale)")
ax.set_xlabel("Date")
ax.legend(loc="best", fontsize=9)
ax.grid(alpha=0.3)
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.tight_layout()
fig.savefig("output/equity.png", dpi=130)
print("wrote output/equity.png")
