#!/usr/bin/env python3
"""ag-15 — equity curve chart: rules A/B/C/D/E, net of taker fees (pooled)."""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

eq = pd.read_csv("output/equity_daily.csv", index_col=0)
eq.index = pd.to_datetime(eq.index)

styles = {
    "A": dict(color="#2e7d32", lw=2.2, ls="-", label="A — crash only (T1)"),
    "B": dict(color="#1565c0", lw=2.2, ls="-", label="B — low-vol down only (T2)"),
    "C": dict(color="#e65100", lw=2.4, ls="-", label="C — combined (T1 OR T2)"),
    "D": dict(color="#8e24aa", lw=1.8, ls=":", label="D — intersection (T1 AND T2)"),
    "E": dict(color="#555555", lw=1.8, ls="--", label="E — always long (baseline)"),
}

fig, ax = plt.subplots(figsize=(11, 6.5))
for r in ["C", "A", "B", "D", "E"]:
    ax.plot(eq.index, eq[r] * 100, **styles[r])

ax.axhline(100, color="grey", lw=0.8)
ax.set_yscale("log")
ax.set_title("ag-15 — Out-of-sample equity, net of taker fees (pooled equal weight per day)")
ax.set_ylabel("Equity index (start = 100, log scale)")
ax.set_xlabel("Date")
ax.legend(loc="best", fontsize=9)
ax.grid(alpha=0.3)
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.tight_layout()
fig.savefig("output/equity.png", dpi=130)
print("wrote output/equity.png")
