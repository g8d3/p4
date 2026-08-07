"""Grid search over S/R grid strategy parameters.

Runs many configs across regimes (multiprocessed) and records metrics. Also
validates the top configs out-of-sample on different data seeds.

Usage:
    python3 optimize.py --search                      # run the parameter sweep
    python3 optimize.py --validate TOPK              # OOS validation of top-K configs
    python3 optimize.py                              # search + validate

Outputs:
    output/optimize/search_results.csv   every tested config + metrics
    output/optimize/top_configs.csv      best configs by score
    output/optimize/validation.csv       OOS validation of top configs
"""

from __future__ import annotations

import argparse
import csv
import faulthandler
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from decimal import Decimal
from itertools import product
from pathlib import Path

# CRITICAL: limit BLAS/OpenMP to ONE thread per process. Without this, every
# worker process spawns one thread per CPU core (OpenBLAS default = all cores),
# so N parallel workers = N * cores threads. On a 6-core laptop 8 workers => 96
# threads => CPU oversubscription and the whole machine freezes.
for _var in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ.setdefault(_var, "1")

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_backtest import load_bars, build_instrument, USD  # noqa: E402
from sr_grid_strategy import SRGridConfig, SRGridStrategy  # noqa: E402

AG_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = AG_DIR / "data"
OUT_DIR = AG_DIR / "output" / "optimize"

BUDGET = Decimal("30000")
START_BALANCE = 100_000.0


@dataclass(frozen=True)
class SearchSpace:
    grid_span_pct: tuple[float, ...] = (1.0, 2.0, 3.5)
    max_levels_per_side: tuple[int, ...] = (4, 6, 8)
    rebalance_interval_bars: tuple[int, ...] = (48, 96, 192)
    max_exposure_budget_mult: tuple[float, ...] = (3.0, 6.0, 10.0)
    trend_filter_enabled: tuple[bool, ...] = (False, True)
    trend_min_dist_pct: tuple[float, ...] = (1.0, 2.0, 3.0)


def run_one(mode: str, overrides: dict) -> dict:
    """Run one config on one regime dataset; return a metrics dict."""
    data_file = DATA_DIR / f"synthetic_5m_{mode}.csv"
    bars, bar_type = load_bars(data_file)
    instrument = build_instrument(bars[0].ts_event)

    from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
    from nautilus_trader.config import LoggingConfig, RiskEngineConfig
    from nautilus_trader.model import Money, Venue
    from nautilus_trader.model.enums import OmsType, AccountType

    config = SRGridConfig(
        instrument_id=instrument.id,
        bar_type=bar_type,
        grid_budget=BUDGET,
        **overrides,
    )
    strategy = SRGridStrategy(config=config)
    engine = BacktestEngine(
        config=BacktestEngineConfig(
            trader_id="TESTER-001",
            risk_engine=RiskEngineConfig(bypass=True),
            logging=LoggingConfig(log_level="ERROR"),
        )
    )
    engine.add_venue(
        venue=Venue("SIM"),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=USD,
        starting_balances=[Money(START_BALANCE, USD)],
    )
    engine.add_instrument(instrument)
    engine.add_strategy(strategy)
    engine.add_data(bars)
    engine.run()

    eq = pd.DataFrame(strategy._equity_curve, columns=["ts", "equity"])
    eq["ret"] = eq["equity"].pct_change()
    eq = eq.dropna()
    total_return = float(eq["equity"].iloc[-1] / eq["equity"].iloc[0] - 1.0) * 100
    std = eq["ret"].std()
    sharpe = float("nan") if std == 0 or np.isnan(std) else (eq["ret"].mean() / std) * np.sqrt(288 * 365)
    dd = float((eq["equity"] / eq["equity"].cummax() - 1.0).min()) * 100
    eq_pos = eq["equity"].iloc[-1]

    pos = pd.DataFrame(strategy._position_curve, columns=["ts", "btc", "usdt", "eq", "px"])
    max_pos = float((pos["btc"].abs() * pos["px"]).max()) if len(pos) else 0.0

    result = {
        "mode": mode,
        "total_return_pct": round(total_return, 3),
        "max_drawdown_pct": round(dd, 3),
        "sharpe": round(sharpe, 3),
        "final_equity": round(float(eq_pos), 1),
        "max_position_usdt": round(max_pos, 0),
        "n_fills": strategy.n_fills,
        "n_rebalances": strategy.n_rebalances,
        "commissions_usdt": round(strategy.total_commissions, 1),
    }
    result.update(overrides)
    return result


def score(row: dict) -> float:
    """Rank mixed results: reward return, penalize drawdown. NaN-safe."""
    if row["final_equity"] <= 0 or pd.isna(row["sharpe"]):
        return -1e9
    return row["total_return_pct"] - 0.5 * abs(row["max_drawdown_pct"])


def _unpack_run(task: tuple) -> dict:
    mode, overrides = task
    return run_one(mode, overrides)


def _worker_init() -> None:
    """Enable hang diagnosis in every worker.

    If a worker runs for more than 90s without returning (a Nautilus hang),
    faulthandler dumps the exact Python stack trace of every thread to stderr
    (which lands in the run log) and then exits the process. This tells us
    WHERE the engine is stuck instead of guessing, and unblocks the executor.
    """
    faulthandler.dump_traceback_later(90, exit=True)


def _task_key(task: tuple) -> tuple:
    mode, overrides = task
    return (mode, tuple(sorted(overrides.items())))


def _append_row(out: Path, result: dict, wrote_header: list) -> None:
    with out.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(result.keys()))
        if not wrote_header[0]:
            w.writeheader()
            wrote_header[0] = True
        w.writerow(result)


def _run_chunk(chunk: list, out: Path, wrote_header: list, workers: int) -> tuple[int, list]:
    """Run a chunk with a per-result watchdog.

    A hung worker would otherwise deadlock `ex.map` forever. A timeout kills
    the executor; the tasks that did not complete are returned for poison
    isolation.
    """
    from concurrent.futures import TimeoutError as FutureTimeout

    done = 0
    with ProcessPoolExecutor(max_workers=workers, max_tasks_per_child=10, initializer=_worker_init) as ex:
        it = ex.map(_unpack_run, chunk, timeout=180)
        try:
            for result in it:
                _append_row(out, result, wrote_header)
                done += 1
        except FutureTimeout:
            print("  ! worker hung: killing executor, isolating lost tasks", flush=True)
            ex.shutdown(wait=False, cancel_futures=True)
        except Exception as exc:
            print(f"  ! executor error: {type(exc).__name__}: {exc}", flush=True)
            ex.shutdown(wait=False, cancel_futures=True)
    lost = chunk[done:]
    return done, lost


def _isolate_poison(lost: list, out: Path, wrote_header: list) -> list:
    """Re-run lost tasks one-by-one with a short timeout to find the poison.

    A deterministic hang (a config that freezes Nautilus) would otherwise be
    re-attempted forever, poisoning every chunk. The offender is returned so it
    can be blacklisted.
    """
    from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeout

    poison = []
    for task in lost:
        try:
            with ProcessPoolExecutor(max_workers=1, initializer=_worker_init) as ex:
                result = next(ex.map(_unpack_run, [task], timeout=45))
            _append_row(out, result, wrote_header)
        except (FutureTimeout, Exception) as exc:
            if isinstance(exc, FutureTimeout):
                print(f"  ! task still stuck individually: {task[0]} {task[1]}", flush=True)
                poison.append(task)
            else:
                print(f"  ! task errored: {type(exc).__name__}: {task[0]}", flush=True)
    return poison


def run_search(regimes=("mixed", "range"), workers: int = 5, limit: int = 0) -> pd.DataFrame:
    space = SearchSpace()
    tasks = []
    for combo in product(
        space.grid_span_pct,
        space.max_levels_per_side,
        space.rebalance_interval_bars,
        space.max_exposure_budget_mult,
        space.trend_filter_enabled,
        space.trend_min_dist_pct,
    ):
        overrides = {
            "grid_span_pct": combo[0],
            "max_levels_per_side": combo[1],
            "rebalance_interval_bars": combo[2],
            "max_exposure_budget_mult": combo[3],
            "trend_filter_enabled": combo[4],
            "trend_min_dist_pct": combo[5],
        }
        for mode in regimes:
            tasks.append((mode, overrides))

    if limit:
        tasks = tasks[:limit]

    # Resume: skip tasks already present in the incremental results file, and
    # skip any known poison (configs that hang Nautilus).
    out = OUT_DIR / "search_results.csv"
    poison_file = OUT_DIR / "poisoned.csv"
    poisoned = set()
    if poison_file.exists() and poison_file.stat().st_size > 0:
        for _, row in pd.read_csv(poison_file).iterrows():
            ov = {c: row[c] for c in row.index if c in ("grid_span_pct", "max_levels_per_side",
                                                          "rebalance_interval_bars", "max_exposure_budget_mult",
                                                          "trend_filter_enabled", "trend_min_dist_pct")}
            poisoned.add((row["mode"], tuple(sorted(ov.items()))))

    done_keys = set()
    if out.exists() and out.stat().st_size > 0:
        existing = pd.read_csv(out)
        for _, row in existing.iterrows():
            ov = {c: row[c] for c in row.index if c in ("grid_span_pct", "max_levels_per_side",
                                                          "rebalance_interval_bars", "max_exposure_budget_mult",
                                                          "trend_filter_enabled", "trend_min_dist_pct")}
            done_keys.add((row["mode"], tuple(sorted(ov.items()))))
    pending = [t for t in tasks if _task_key(t) not in done_keys and _task_key(t) not in poisoned]
    print(f"  {len(done_keys)} already done, {len(poisoned)} poisoned, "
          f"running {len(pending)} more", flush=True)

    wrote_header = [out.exists() and out.stat().st_size > 0]
    CHUNK = 60
    total_done = 0
    for start in range(0, len(pending), CHUNK):
        chunk = pending[start:start + CHUNK]
        done, lost = _run_chunk(chunk, out, wrote_header, workers)
        total_done += done
        print(f"  chunk {start // CHUNK + 1}: {done}/{len(chunk)} done "
              f"(total {len(done_keys) + total_done}/{len(tasks)})", flush=True)
        if lost:
            new_poison = _isolate_poison(lost, out, wrote_header)
            if new_poison:
                poisoned.update(_task_key(t) for t in new_poison)
                with poison_file.open("a", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=list(new_poison[0][1].keys()) + ["mode"])
                    if poison_file.stat().st_size == 0:
                        w.writeheader()
                    for t in new_poison:
                        w.writerow({**t[1], "mode": t[0]})

    return pd.read_csv(out)


def run_validation(top: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Validate the top configs out-of-sample on unseen seeds, all 4 regimes."""
    seeds = [7, 13, 99]
    modes = ("range", "mixed", "trend", "downtrend")
    import gen_synthetic_data as gen

    for seed in seeds:
        for mode in modes:
            df = gen.generate(20_000, seed=seed, start_price=30_000.0, mode=mode)
            df.to_csv(DATA_DIR / f"oos_{mode}_seed{seed}.csv", index=False)

    top_cfg = top[top["mode"] == "mixed"].head(n)
    cols = ["grid_span_pct", "max_levels_per_side", "rebalance_interval_bars",
            "max_exposure_budget_mult", "trend_filter_enabled", "trend_min_dist_pct"]
    rows = []
    for i, cfg_row in top_cfg.iterrows():
        overrides = {c: cfg_row[c] for c in cols}
        for mode in modes:
            for seed in seeds:
                data_file = DATA_DIR / f"oos_{mode}_seed{seed}.csv"
                res = run_one_on(data_file, overrides)
                res["seed"] = seed
                res["mode"] = mode
                res["config"] = i
                rows.append(res)
    return pd.DataFrame(rows)


def run_one_on(data_file: Path, overrides: dict) -> dict:
    bars, bar_type = load_bars(data_file)
    instrument = build_instrument(bars[0].ts_event)

    from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
    from nautilus_trader.config import LoggingConfig, RiskEngineConfig
    from nautilus_trader.model import Money, Venue
    from nautilus_trader.model.enums import OmsType, AccountType

    config = SRGridConfig(
        instrument_id=instrument.id, bar_type=bar_type, grid_budget=BUDGET, **overrides
    )
    strategy = SRGridStrategy(config=config)
    engine = BacktestEngine(
        config=BacktestEngineConfig(
            trader_id="TESTER-001",
            risk_engine=RiskEngineConfig(bypass=True),
            logging=LoggingConfig(log_level="ERROR"),
        )
    )
    engine.add_venue(
        venue=Venue("SIM"), oms_type=OmsType.NETTING, account_type=AccountType.MARGIN,
        base_currency=USD, starting_balances=[Money(START_BALANCE, USD)],
    )
    engine.add_instrument(instrument)
    engine.add_strategy(strategy)
    engine.add_data(bars)
    engine.run()

    eq = pd.DataFrame(strategy._equity_curve, columns=["ts", "equity"])
    eq["ret"] = eq["equity"].pct_change()
    eq = eq.dropna()
    total_return = float(eq["equity"].iloc[-1] / eq["equity"].iloc[0] - 1.0) * 100
    dd = float((eq["equity"] / eq["equity"].cummax() - 1.0).min()) * 100
    return {
        "total_return_pct": round(total_return, 3),
        "max_drawdown_pct": round(dd, 3),
        "final_equity": round(float(eq["equity"].iloc[-1]), 1),
    }


def show_status() -> None:
    """Print live progress and the best configs found so far."""
    out = OUT_DIR / "search_results.csv"
    if not out.exists():
        print("No search results yet.")
        return
    df = pd.read_csv(out)
    df["score"] = df.apply(score, axis=1)
    total = 972
    print(f"Progreso: {len(df)}/{total} configs evaluados  "
          f"({len(df[df['mode']=='range'])} range, {len(df[df['mode']=='mixed'])} mixed)")
    if df.empty:
        return
    cols = ["mode", "total_return_pct", "max_drawdown_pct", "sharpe", "max_position_usdt",
            "grid_span_pct", "max_levels_per_side", "rebalance_interval_bars",
            "max_exposure_budget_mult", "trend_filter_enabled", "trend_min_dist_pct", "score"]
    for mode in ("range", "mixed"):
        sub = df[df["mode"] == mode]
        if sub.empty:
            continue
        top = sub.sort_values("score", ascending=False).head(4)
        print(f"\n== Top {mode} ==")
        print(top[cols].to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--search", action="store_true", help="run the parameter sweep")
    parser.add_argument("--validate", type=int, default=0, help="validate top N configs OOS")
    parser.add_argument("--no-search", action="store_true")
    parser.add_argument("--status", action="store_true",
                        help="show live progress + best configs so far (no runs)")
    parser.add_argument("--workers", type=int, default=5,
                        help="parallel worker processes (keep <= physical cores/2 to avoid CPU oversubscription)")
    parser.add_argument("--limit", type=int, default=0,
                        help="only run the first N configs (sanity check)")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.status:
        show_status()
        return

    if not args.no_search or args.search:
        print("=== SEARCH ===", flush=True)
        df = run_search(workers=args.workers, limit=args.limit)
        df["score"] = df.apply(score, axis=1)
        top = df.sort_values("score", ascending=False)
        top.to_csv(OUT_DIR / "top_configs.csv", index=False)
        print(top.head(12).to_string(index=False))
    else:
        df = pd.read_csv(OUT_DIR / "search_results.csv")
        top = pd.read_csv(OUT_DIR / "top_configs.csv")

    n = args.validate or 5
    print(f"\n=== OUT-OF-SAMPLE VALIDATION (top {n}) ===", flush=True)
    val = run_validation(top, n)
    val.to_csv(OUT_DIR / "validation.csv", index=False)
    print(val.to_string(index=False))


if __name__ == "__main__":
    main()
