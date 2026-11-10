#!/usr/bin/env python3
"""e109 — energy of one job, in microjoules. The RAPL counter is root-only on this box."""
import subprocess
from pathlib import Path


def energy_uj(counter):
    try:
        return int(Path(counter).read_text().strip())
    except Exception:
        pass
    out = subprocess.run(["sudo", "-n", "cat", counter], capture_output=True, text=True)
    try:
        return int(out.stdout.strip())
    except Exception:
        return None


def joules_between(counter, fn):
    """Run fn, return (result, joules). joules is None when no counter is readable."""
    e0 = energy_uj(counter)
    result = fn()
    e1 = energy_uj(counter)
    if e0 is None or e1 is None:
        return result, None
    return result, (e1 - e0) / 1e6
