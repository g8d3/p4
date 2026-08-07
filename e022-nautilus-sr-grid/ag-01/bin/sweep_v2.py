"""Sweep v2 configs across real BTC datasets, appending to a results CSV.

Each config is one row: strategy params + key metrics. Runs backtests
sequentially (Nautilus leaks ~25MB/run, so a single process keeps it bounded).

Usage:
    python3 bin/sweep_v2.py [--data real_btc_5m.csv] [--out output/v2_sweep_5m.csv]
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

AG_DIR = Path(__file__).resolve().parents[1]
BIN = AG_DIR / "bin"
RUN = BIN / "run_backtest.py"

CONFIGS_5M = [
    # (tag, [extra args])  -- base args applied uniformly
    ("reb192_atr20", ["--atr-mult", "2.0", "--max-levels", "2", "--min-order", "1000", "--trend-fast", "50", "--trend-slow", "100", "--trend-enter", "1.0", "--trend-exit", "0.5", "--rebalance", "192"]),
    ("reb192_atr25", ["--atr-mult", "2.5", "--max-levels", "2", "--min-order", "1000", "--trend-fast", "50", "--trend-slow", "100", "--trend-enter", "1.0", "--trend-exit", "0.5", "--rebalance", "192"]),
    ("reb192_atr30", ["--atr-mult", "3.0", "--max-levels", "2", "--min-order", "1000", "--trend-fast", "50", "--trend-slow", "100", "--trend-enter", "1.0", "--trend-exit", "0.5", "--rebalance", "192"]),
    ("reb288_atr25", ["--atr-mult", "2.5", "--max-levels", "2", "--min-order", "1000", "--trend-fast", "50", "--trend-slow", "100", "--trend-enter", "1.0", "--trend-exit", "0.5", "--rebalance", "288"]),
    ("reb384_atr25", ["--atr-mult", "2.5", "--max-levels", "2", "--min-order", "1000", "--trend-fast", "50", "--trend-slow", "100", "--trend-enter", "1.0", "--trend-exit", "0.5", "--rebalance", "384"]),
    ("reb192_atr25_ent15", ["--atr-mult", "2.5", "--max-levels", "2", "--min-order", "1000", "--trend-fast", "50", "--trend-slow", "100", "--trend-enter", "1.5", "--trend-exit", "0.7", "--rebalance", "192"]),
    ("reb192_atr25_lv3", ["--atr-mult", "2.5", "--max-levels", "3", "--min-order", "1000", "--trend-fast", "50", "--trend-slow", "100", "--trend-enter", "1.0", "--trend-exit", "0.5", "--rebalance", "192"]),
    ("reb192_atr25_min2000", ["--atr-mult", "2.5", "--max-levels", "2", "--min-order", "2000", "--trend-fast", "50", "--trend-slow", "100", "--trend-enter", "1.0", "--trend-exit", "0.5", "--rebalance", "192"]),
]

CONFIGS_1H = [
    ("atr25_lv2_min1000", ["--atr-mult", "2.5", "--max-levels", "2", "--min-order", "1000"]),
    ("atr30_lv2_min1000", ["--atr-mult", "3.0", "--max-levels", "2", "--min-order", "1000"]),
    ("atr20_lv2_min1000", ["--atr-mult", "2.0", "--max-levels", "2", "--min-order", "1000"]),
    ("atr25_lv3_min1000", ["--atr-mult", "2.5", "--max-levels", "3", "--min-order", "1000"]),
    ("atr25_lv2_trend50200", ["--atr-mult", "2.5", "--max-levels", "2", "--min-order", "1000", "--trend-fast", "50", "--trend-slow", "200", "--trend-enter", "1.0", "--trend-exit", "0.5"]),
    ("atr25_lv2_trend50_100", ["--atr-mult", "2.5", "--max-levels", "2", "--min-order", "1000", "--trend-fast", "50", "--trend-slow", "100", "--trend-enter", "1.0", "--trend-exit", "0.5"]),
]


def run_one(data: Path, tag: str, extra: list[str], budget: str, rebalance: str) -> dict:
    out_dir = AG_DIR / "output" / f"v2_sweep_{data.stem}_{tag}"
    cmd = [
        sys.executable, str(RUN),
        "--strategy", "v2",
        "--data", str(data),
        "--out-dir", str(out_dir),
        "--budget", budget,
        "--rebalance", rebalance,
        "--log-level", "ERROR",
    ] + extra
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    if proc.returncode != 0:
        return {"tag": tag, "error": proc.stderr[-2000:]}
    metrics_path = out_dir / "metrics.json"
    if not metrics_path.exists():
        return {"tag": tag, "error": f"no metrics.json in {out_dir}"}
    metrics = json.loads(metrics_path.read_text())
    row = {
        "tag": tag,
        "extra": " ".join(extra),
        "data": data.name,
        "return_pct": metrics.get("total_return_pct"),
        "max_dd_pct": metrics.get("max_drawdown_pct"),
        "n_fills": metrics.get("n_fills"),
        "n_regime_flips": metrics.get("n_regime_flips"),
        "n_cap_enforcements": metrics.get("n_cap_enforcements"),
        "n_liquidations": metrics.get("n_liquidations"),
        "commissions": metrics.get("total_commissions_usdt"),
        "profit_factor": metrics.get("profit_factor"),
        "final_equity": metrics.get("final_equity_usdt"),
    }
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=str, default="real_btc_5m.csv")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--budget", type=str, default="30000")
    parser.add_argument("--rebalance", type=str, default="96")
    args = parser.parse_args()

    data = AG_DIR / "data" / args.data
    if not data.exists():
        print(f"data file not found: {data}")
        sys.exit(1)

    configs = CONFIGS_1H if "1h" in args.data else CONFIGS_5M
    out = args.out or AG_DIR / "output" / f"v2_sweep_{data.stem}.csv"

    rows = []
    for tag, extra in configs:
        print(f"RUN {tag} ...", flush=True)
        row = run_one(data, tag, extra, args.budget, args.rebalance)
        print(f"  -> {row.get('return_pct')}% dd={row.get('max_dd_pct')}% fills={row.get('n_fills')} flips={row.get('n_regime_flips')} cap={row.get('n_cap_enforcements')} fees={row.get('commissions')} pf={row.get('profit_factor')}", flush=True)
        rows.append(row)

    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
