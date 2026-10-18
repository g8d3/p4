#!/usr/bin/env python3
"""Tests for the regression gate — the artifact that outlives the audit.

    python3 tests/gate-test.py

Deterministic fixtures only (no live log): a baseline window, the same window (must PASS), a
30% slower window (must FAIL on wall), and a window with 8% wasted turns (must FAIL on waste
while its wall is fine). Plus the two things a gate must never do: crash on an empty log, and
silently re-baseline itself.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
GATE = PACK / "regression_gate.py"
fails: list[str] = []


def check(name: str, ok: bool, extra: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f" — {extra}" if extra else ""))
    if not ok:
        fails.append(name)


def row(i: int, wall: int, outcome: str = "completed", out: int = 100, pre: int = 400) -> dict:
    return {"ts": f"2026-01-01T10:{i:02d}:00.000Z", "sessionId": "s1", "model": "m1", "turnIndex": i,
            "llmDurationMs": wall // 2, "preResponseMs": pre, "toolMsTotal": 10, "turnMsTotal": wall,
            "input": 100, "output": out, "outcome": outcome}


def write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def gate(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(GATE), *args], capture_output=True, text=True)


tmp = Path(tempfile.mkdtemp())
base_rows = [row(i, 1000 + i * 10) for i in range(1, 21)]
slow_rows = [row(i, 1500 + i * 10) for i in range(1, 21)]          # +50% wall
waste_rows = [row(i, 1000 + i * 10, outcome="error", out=0) if i <= 2 else row(i, 1000 + i * 10)
              for i in range(1, 21)]                               # 2/20 = 10% wasted
base_log, slow_log, waste_log = tmp / "base.jsonl", tmp / "slow.jsonl", tmp / "waste.jsonl"
empty_log = tmp / "empty.jsonl"
write(base_log, base_rows); write(slow_log, slow_rows)
write(waste_log, waste_rows); empty_log.write_text("")
baseline = tmp / "baseline.json"

r = gate("--log", str(base_log), "--baseline", str(baseline), "--write-baseline")
check("write-baseline exits 0 and names the file", r.returncode == 0 and baseline.exists())
bl = json.loads(baseline.read_text())
check("baseline records the medians and the limits",
      all(k in bl for k in ("wall_p50_ms", "wasted_rate_pct", "wall_factor", "created", "source")),
      f"wall p50 {bl.get('wall_p50_ms')} ms")

r = gate("--log", str(base_log), "--baseline", str(baseline))
check("the same window passes", r.returncode == 0 and "PASS" in r.stdout, r.stdout.strip().splitlines()[-1])

r = gate("--log", str(slow_log), "--baseline", str(baseline))
check("a 50% slower window fails on wall", r.returncode == 1 and "FAIL" in r.stdout, r.stdout.strip().splitlines()[-3])

r = gate("--log", str(waste_log), "--baseline", str(baseline))
check("a 10% wasted-turn window fails on waste", r.returncode == 1 and "wasted-turn rate" in r.stdout)

r = gate("--log", str(empty_log), "--baseline", str(baseline))
check("an empty log is refused, not silently passed", r.returncode != 0 and "no usable turn" in (r.stdout + r.stderr))

r = gate("--log", str(base_log), "--baseline", tmp / "does-not-exist.json")
check("a missing baseline is an error, not implicit re-baselining", r.returncode != 0)
# ...and it is a message a client can act on, not a traceback: this script runs unattended
# on someone else's machine, so its failures have to explain themselves.
check("a missing baseline explains what to run, without a traceback",
      "no baseline at" in r.stdout and "--write-baseline" in r.stdout
      and "Traceback" not in r.stdout + r.stderr,
      r.stdout.strip().splitlines()[0] if r.stdout.strip() else "")
bad = tmp / "bad-baseline.json"
bad.write_text("{not json")
r = gate("--log", str(base_log), "--baseline", str(bad))
check("a corrupt baseline is a message too, not a traceback",
      "not valid JSON" in r.stdout and "Traceback" not in r.stdout + r.stderr)

# the gate must report the provider roundtrip without failing on it: double it and keep wall flat
pre_rows = [row(i, 1000 + i * 10, pre=800) for i in range(1, 21)]
pre_log = tmp / "pre.jsonl"; write(pre_log, pre_rows)
r = gate("--log", str(pre_log), "--baseline", str(baseline))
check("a provider roundtrip change is reported, not failed", r.returncode == 0 and "provider roundtrip" in r.stdout,
      [l for l in r.stdout.splitlines() if "note:" in l][:1])

# stdlib only: run it with -S (no site packages) to prove there is no hidden dependency
r = subprocess.run([sys.executable, "-S", str(GATE), "--log", str(base_log), "--baseline", str(baseline)],
                   capture_output=True, text=True)
check("runs with no site-packages (stdlib only)", r.returncode == 0, r.stderr.strip()[:80])

print(f"\n{len(fails)} failing check(s)")
sys.exit(1 if fails else 0)
