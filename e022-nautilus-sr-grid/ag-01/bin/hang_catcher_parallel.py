"""Concurrent hang catcher: replicate the conditions that produced the original
Nautilus hang (optimize.py: 8 parallel workers + BLAS oversubscription).

The historical hang (~1/50 runs, stuck in a futex) appeared under parallel
workers. A sequential harness may never reproduce it, so this runs `workers`
backtests simultaneously (like the original search) while arming
`faulthandler.dump_traceback_later` in each child. When a child hangs, its
log gets a full Python stack dump before exit; the parent kills stragglers.

Usage:
    python3 hang_catcher_parallel.py [--workers 6] [--rounds 20] [--timeout 120]
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

AG_DIR = Path(__file__).resolve().parents[1]
RUN = AG_DIR / "bin" / "run_backtest.py"

CHILD_SNIPPET = """
import faulthandler, sys
faulthandler.dump_traceback_later(%(timeout)d, exit=True)
sys.path.insert(0, %(bindir)r)
from run_backtest import main
import sys as _s
_s.argv = %(argv)r
try:
    main()
except SystemExit:
    pass
print("CHILD_OK", flush=True)
"""


def spawn(data: Path, out_dir: Path, tag: str, timeout_s: int) -> subprocess.Popen:
    argv = [
        str(RUN),
        "--strategy", "v2",
        "--data", str(data),
        "--out-dir", str(out_dir / f"{tag}_out"),
        "--budget", "30000",
        "--rebalance", "192",
        "--log-level", "ERROR",
        "--atr-mult", "2.5", "--max-levels", "2", "--min-order", "1000",
        "--trend-fast", "50", "--trend-slow", "100",
        "--trend-enter", "1.0", "--trend-exit", "0.5",
    ]
    snippet = CHILD_SNIPPET % {
        "timeout": timeout_s,
        "bindir": str(RUN.parent),
        "argv": argv,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen(
        [sys.executable, "-c", snippet],
        stdout=open(out_dir / f"{tag}.log", "w"),
        stderr=subprocess.STDOUT,
        env={**os.environ, "OPENBLAS_NUM_THREADS": "4", "OMP_NUM_THREADS": "4"},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=str, default="real_btc_1h.csv")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--rounds", type=int, default=20, help="waves of `workers` runs")
    parser.add_argument("--timeout", type=int, default=90, help="per-run hang timeout (s)")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    data = AG_DIR / "data" / args.data
    if not data.exists():
        print(f"data file not found: {data}")
        sys.exit(1)
    out = args.out or AG_DIR / "output" / "hang_catcher_parallel"
    out.mkdir(parents=True, exist_ok=True)

    hangs = 0
    round_no = 0
    while round_no < args.rounds and hangs < 3:
        round_no += 1
        procs = {}
        for w in range(args.workers):
            tag = f"r{round_no:03d}_w{w}"
            procs[tag] = spawn(data, out, tag, args.timeout)

        deadline = time.time() + args.timeout + 15
        for tag, proc in list(procs.items()):
            remain = max(0.1, deadline - time.time())
            try:
                proc.communicate(timeout=remain)
                status = "ok" if proc.returncode == 0 else f"exit{proc.returncode}"
            except subprocess.TimeoutExpired:
                os.kill(proc.pid, signal.SIGKILL)
                proc.wait()
                status = "HANG"
            if status == "HANG":
                hangs += 1
                print(f"[round {round_no}] {tag}: *** HANG CAPTURED — dump in {out}/{tag}.log ***", flush=True)
            elif status != "ok":
                print(f"[round {round_no}] {tag}: {status} (check {out}/{tag}.log)", flush=True)
        print(f"[round {round_no}/{args.rounds}] done: {args.workers} runs, {hangs} hang(s) so far", flush=True)

    print(f"finished: {hangs} hang(s) in {round_no * args.workers} runs", flush=True)


if __name__ == "__main__":
    main()
