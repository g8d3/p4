#!/usr/bin/env python3
"""Aggregate per-regime metrics.json files into a summary CSV.

Usage:
    python3 summarize.py [--out-dir output]
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

COLS = [
    "mode",
    "total_return_pct",
    "total_pnl_usdt",
    "sharpe",
    "max_drawdown_pct",
    "n_fills",
    "n_positions",
    "total_commissions_usdt",
    "profit_factor",
    "win_rate_pct",
    "final_equity_usdt",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parents[1] / "output")
    args = parser.parse_args()

    rows = []
    for child in sorted(args.out_dir.iterdir()):
        metrics = child / "metrics.json"
        if not metrics.is_file():
            continue
        d = json.loads(metrics.read_text())
        d = {"mode": child.name, **d}
        rows.append({k: d.get(k) for k in COLS})

    out = args.out_dir / "summary.csv"
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {out}")
    with out.open() as f:
        print(f.read())


if __name__ == "__main__":
    main()
