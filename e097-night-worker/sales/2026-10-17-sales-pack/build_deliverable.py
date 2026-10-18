#!/usr/bin/env python3
"""The public sample of `breakdown.md` — now a one-line flag on the delivery engine.

The generator, the arithmetic and the labelling all live in `audit_report.py`, so the page
we show prospects and the page we hand a client come out of the same code. This wrapper
exists only because the pack (and the README) has always called it:

    python3 build_deliverable.py     -> deliverables-sample.html (+ .md for review)

`--sample` means: use our own published one-word-turn numbers (371 + 1554 + 3 ms, etc.)
and the example volume, and label every figure [measured] / [example] / [assumption]. A
client run is the same command with `--answers` and `--log` instead of `--sample`.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "deliverables-sample.html"
MD = HERE / "deliverables-sample.md"


def main() -> None:
    cmd = [sys.executable, str(HERE / "audit_report.py"), "--sample",
           "--out", str(MD), "--html", str(OUT)]
    subprocess.run(cmd, check=True)
    text = OUT.read_text()
    for tag in ("code", "strong", "em", "a"):
        if text.count(f"<{tag}") != text.count(f"</{tag}>"):
            raise SystemExit(f"unbalanced <{tag}> in {OUT.name}")
    if "«" in text:
        raise SystemExit("an unfilled placeholder reached the published sample")
    print(f"sample built from the delivery engine: {OUT.name} "
          f"({len(text) / 1024:.0f} KB), {text.count('class=\"tag\"')} labelled figures")


if __name__ == "__main__":
    main()
