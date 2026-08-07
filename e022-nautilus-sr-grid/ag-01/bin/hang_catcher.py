"""Hang catcher: run Nautilus backtests in fresh subprocesses until one hangs,
capturing the faulthandler stack dump.

The Nautilus hang is transient (~1/50 runs) and stuck in a futex — the
previous search only survived it via watchdog + resume. This harness runs a
long series of single backtests, each in its own subprocess with
`faulthandler.dump_traceback_later` armed, so when a run freezes the Python
stack of every thread is dumped to that run's log before the process exits.
Parent-side timeout + kill guarantees no deadlock even if faulthandler misses.

Usage:
    python3 hang_catcher.py [--data real_btc_5m.csv] [--runs 60] [--timeout 120]
                            [--out output/hang_catcher]
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

CHILD_SNIPPET = r'''
import faulthandler, sys, time
faulthandler.dump_traceback_later({timeout}, exit=True)
sys.path.insert(0, {bin_q!r})
from run_backtest import main
import argparse
import sys as _s
argv = {argv!r}
_sys_argv = _s.argv
_s.argv = argv
try:
    main()
except SystemExit:
    pass
print("CHILD_OK", flush=True)
'''

CHILD_SNIPPET_2 = """
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


def run_once(data: Path, out_dir: Path, tag: str, timeout_s: int) -> dict:
    argv = [
        str(RUN),
        "--strategy", "v2",
        "--data", str(data),
        "--out-dir", str(out_dir),
        "--budget", "30000",
        "--rebalance", "192",
        "--log-level", "ERROR",
        "--atr-mult", "2.5", "--max-levels", "2", "--min-order", "1000",
        "--trend-fast", "50", "--trend-slow", "100",
        "--trend-enter", "1.0", "--trend-exit", "0.5",
    ]
    snippet = CHILD_SNIPPET_2 % {
        "timeout": timeout_s,
        "bindir": str(RUN.parent),
        "argv": argv,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    log = out_dir / f"{tag}.log"
    started = time.time()
    try:
        proc = subprocess.Popen(
            [sys.executable, "-c", snippet],
            stdout=open(log, "w"),
            stderr=subprocess.STDOUT,
        )
        try:
            proc.communicate(timeout=timeout_s + 10)
            rc = proc.returncode
            status = "ok" if rc == 0 else f"exit{rc}"
        except subprocess.TimeoutExpired:
            os.kill(proc.pid, signal.SIGKILL)
            proc.wait()
            status = "HANG"
    except Exception as exc:  # pragma: no cover
        return {"tag": tag, "status": f"error:{exc}", "seconds": round(time.time() - started, 1)}
    return {"tag": tag, "status": status, "seconds": round(time.time() - started, 1)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=str, default="real_btc_5m.csv")
    parser.add_argument("--runs", type=int, default=60)
    parser.add_argument("--timeout", type=int, default=120, help="per-run hang timeout (s)")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    data = AG_DIR / "data" / args.data
    if not data.exists():
        print(f"data file not found: {data}")
        sys.exit(1)
    out = args.out or AG_DIR / "output" / "hang_catcher"
    out.mkdir(parents=True, exist_ok=True)

    hangs = 0
    for i in range(1, args.runs + 1):
        tag = f"run{i:03d}"
        r = run_once(data, out, tag, args.timeout)
        print(f"[{i}/{args.runs}] {tag}: {r['status']} in {r['seconds']}s", flush=True)
        if r["status"] == "HANG":
            hangs += 1
            print(f"  *** HANG CAPTURED in {tag}: dump in {out}/{tag}.log ***", flush=True)
            # keep going to see if it reproduces, but stop once confirmed
            if hangs >= 2:
                print("two hangs captured — stopping", flush=True)
                break

    print(f"done: {hangs} hang(s) in {i} runs", flush=True)


if __name__ == "__main__":
    main()
