"""Out-of-sample search for v2 on REAL BTC with a train/test split.

The v1 optimization (`optimize.py`) searched on synthetic data, which did not
transfer to real markets. v2 was tuned by hand on the full real dataset, which
risks overfitting to the whole sample. This script does the proper split:

1. Split each real CSV by time (first 60% = train, last 40% = test).
2. Grid-search a small v2 parameter space on TRAIN.
3. Re-run the top-N train configs on TEST (never seen during selection).
4. Report the train/test pairs so an honest read of the out-of-sample edge
   (or its absence) is possible.

Each config runs in its own `subprocess` invoking `run_backtest.py` with a
train/test slice. This is deliberate: in-process workers that import Nautilus
(fork) or reuse a parent pool (spawn) reproduce the historical Nautilus hang
(fork + jemalloc background-thread deadlock). 478 standalone subprocess runs
never hung, so subprocess-per-config is the proven-safe execution model.

Usage:
    python3 optimize_v2_oos.py --data real_btc_5m.csv [--workers 5]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

AG_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = AG_DIR / "data"
OUT_DIR = AG_DIR / "output" / "optimize_v2_oos"
RUN = AG_DIR / "bin" / "run_backtest.py"

BUDGET = "30000"
START_BALANCE = 100_000.0
TRAIN_FRAC = 0.6

# Split bars by time and write a temporary CSV slice so the worker (a clean
# subprocess) loads only that slice. Nautilus never loads in this parent.
def write_split(data_file: Path, frac: float, out_dir: Path) -> tuple[Path, Path]:
    df = pd.read_csv(data_file)
    cut = max(1, int(len(df) * frac))
    train_df, test_df = df.iloc[:cut], df.iloc[cut:]
    out_dir.mkdir(parents=True, exist_ok=True)
    train_path = out_dir / f"{data_file.stem}_train.csv"
    test_path = out_dir / f"{data_file.stem}_test.csv"
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)
    return train_path, test_path


@dataclass(frozen=True)
class SearchSpace:
    grid_atr_mult: tuple[float, ...] = (2.0, 2.5, 3.0)
    max_levels_per_side: tuple[int, ...] = (2, 3)
    rebalance_interval_bars: tuple[int, ...] = (96, 144, 192)
    max_exposure_budget_mult: tuple[float, ...] = (3.0, 4.0)
    trend_enter_pct: tuple[float, ...] = (1.0, 1.5)
    trend_exit_pct: tuple[float, ...] = (0.5, 0.7)


def product(space: SearchSpace):
    for a in space.grid_atr_mult:
        for b in space.max_levels_per_side:
            for c in space.rebalance_interval_bars:
                for d in space.max_exposure_budget_mult:
                    for e, f in zip(space.trend_enter_pct, space.trend_exit_pct):
                        yield {
                            "grid_atr_mult": a,
                            "max_levels_per_side": b,
                            "rebalance_interval_bars": c,
                            "max_exposure_budget_mult": d,
                            "trend_enter_pct": e,
                            "trend_exit_pct": f,
                        }


def run_one(data_path: Path, overrides: dict, scratch: Path, tag: str) -> dict:
    """Run one config in a fresh subprocess; return metrics + overrides."""
    out_dir = scratch / f"{tag}_out"
    cmd = [
        sys.executable,
        str(RUN),
        "--strategy", "v2",
        "--data", str(data_path),
        "--out-dir", str(out_dir),
        "--budget", BUDGET,
        "--log-level", "ERROR",
        "--atr-mult", str(overrides["grid_atr_mult"]),
        "--max-levels", str(overrides["max_levels_per_side"]),
        "--rebalance", str(overrides["rebalance_interval_bars"]),
        "--max-exposure-mult", str(overrides["max_exposure_budget_mult"]),
        "--trend-enter", str(overrides["trend_enter_pct"]),
        "--trend-exit", str(overrides["trend_exit_pct"]),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    metrics_path = out_dir / "metrics.json"
    if proc.returncode != 0 or not metrics_path.exists():
        raise RuntimeError(
            f"run {tag} failed rc={proc.returncode}: {proc.stderr[-500:]}"
        )
    m = json.loads(metrics_path.read_text())
    return {
        "total_return_pct": m.get("total_return_pct"),
        "max_drawdown_pct": m.get("max_drawdown_pct"),
        "n_fills": m.get("n_fills"),
        "commissions_usdt": m.get("total_commissions_usdt"),
        "final_equity_usdt": m.get("final_equity_usdt"),
        **overrides,
    }


def _task(args) -> dict:
    data_path, overrides, scratch, tag, split = args
    result = run_one(data_path, overrides, scratch, f"{split}_{tag}")
    result.update({"split": split})
    return result


def sweep(data_path: Path, configs: list, scratch: Path, split: str, workers: int) -> list:
    """Run all configs on one split, parallel via threads (each spawns a
    subprocess). Returns list of result dicts."""
    tasks = [
        (data_path, ov, scratch, f"c{i:03d}", split)
        for i, ov in enumerate(configs)
    ]
    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_task, t): t[3] for t in tasks}
        for fut in as_completed(futs):
            tag = futs[fut]
            try:
                results.append(fut.result())
            except Exception as exc:
                print(f"  ! {split}/{tag} failed: {type(exc).__name__}: {exc}", flush=True)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=str, default="real_btc_5m.csv")
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--top-n", type=int, default=5)
    args = parser.parse_args()

    data_file = DATA_DIR / args.data
    if not data_file.exists():
        print(f"data file not found: {data_file}")
        sys.exit(1)

    scratch = Path(tempfile.mkdtemp(prefix="oos_"))
    train_csv, test_csv = write_split(data_file, TRAIN_FRAC, scratch)
    df_all = pd.read_csv(data_file)
    print(
        f"{args.data}: {len(df_all)} bars -> "
        f"{int(len(df_all)*TRAIN_FRAC)} train / {len(df_all)-int(len(df_all)*TRAIN_FRAC)} test",
        flush=True,
    )

    out = OUT_DIR / data_file.stem
    out.mkdir(parents=True, exist_ok=True)

    configs = list(product(SearchSpace()))
    print(f"searching {len(configs)} configs on TRAIN ({args.workers} workers)", flush=True)
    train_results = sweep(train_csv, configs, scratch, "train", args.workers)
    df = pd.DataFrame(train_results).sort_values("total_return_pct", ascending=False)
    train_csv_out = out / "train_results.csv"
    df.to_csv(train_csv_out, index=False)
    print(f"train sweep -> {train_csv_out}")
    print(df.head(10).to_string())

    top = df.head(args.top_n)
    top_configs = [dict(r[["grid_atr_mult", "max_levels_per_side", "rebalance_interval_bars",
                           "max_exposure_budget_mult", "trend_enter_pct", "trend_exit_pct"]]) for _, r in top.iterrows()]
    print(f"validating top {len(top_configs)} on TEST", flush=True)
    test_results = sweep(test_csv, top_configs, scratch, "test", min(args.workers, len(top_configs)))
    test_df = pd.DataFrame(test_results)
    test_csv_out = out / "test_results.csv"
    test_df.to_csv(test_csv_out, index=False)
    print(f"test validation -> {test_csv_out}")

    keys = ["grid_atr_mult", "max_levels_per_side", "rebalance_interval_bars",
            "max_exposure_budget_mult", "trend_enter_pct", "trend_exit_pct"]
    train_idx = df.set_index(keys)
    test_idx = test_df.set_index(keys)
    summary = pd.DataFrame({
        "train_return": train_idx["total_return_pct"],
        "test_return": test_idx["total_return_pct"],
        "test_dd": test_idx["max_drawdown_pct"],
        "test_fills": test_idx["n_fills"],
        "test_commissions": test_idx["commissions_usdt"],
    }).reset_index()
    summary_csv = out / "oos_summary.csv"
    summary.to_csv(summary_csv, index=False)
    print(f"OOS summary -> {summary_csv}")
    print(summary.to_string())


if __name__ == "__main__":
    main()
