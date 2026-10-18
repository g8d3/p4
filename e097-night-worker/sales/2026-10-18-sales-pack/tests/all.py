#!/usr/bin/env python3
"""One command that runs every check in this pack, in the order that fails fastest.

    python3 tests/all.py            # against what is live (focalis.cc + the repos)
    python3 tests/all.py --local    # against the local build artifacts only (no network)

Why: the pack has fifteen checks now and they used to be run one at a time all night. A pack whose
verification needs a human to remember fifteen commands is a pack that will be published
unverified. Exit code is non-zero if anything fails.

What each one protects (a claim, not a file):

  roi-parity       the calculator in the browser and `roi.py` agree on 63 cases
  roi-browser      the deployed offer page renders those same numbers
  audit-report     the delivery engine: published sample figures + a client report that
                   carries none of our constants
  gate             the regression gate fails when the tax comes back and passes when it does not
  preview-parity   the free preview's arithmetic == a Python mirror (JSONL *and* mapped CSV)
  deliverable      the sample deliverable page as served: labels, arithmetic, links, phone width
  company-pages    the seller pages a payment provider reads (who sells, terms, refunds, privacy)
                   and the private forwarding address never being served again
  routes-page      the published route matrix == the measured matrix (price and latency ratios)
  matrix-prices    every published route price is still the price the provider publishes today
  procsplit-claims the published boot/pre/stream numbers == the two raw runs, and the money
  paper-matrix     the paper §10 table and its counts == the generated route matrix
  fleet-window     the fleet numbers on the pages == the window we publish (`fleet/`)
  bench-claims     the "2.4–3.4 s median no-op turn" headline == the published bench.csv
  offer-mirror     the offer exists once: /tps/audit/ and GitHub Pages are pointers, not copies
  sample-repro     the four published Tier 2 examples regenerate byte-for-byte from the published
                   fleet window + the published answers file (no rotating live window)
  funnel-links     every hop from the site root to the inbox resolves, anchors included
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent
LOCAL = "--local" in sys.argv

# Where the paper's repository is on THIS machine: the pack is not in the repository, so the
# suites find it through the environment. The machine path lives here (a pack-only file), never
# inside the published tests.
ENV = os.environ.copy()
for _cand in (os.environ.get("REPO_ROOT"), "/home/vuos/srv/tps", "/tmp/night/report-pub"):
    if _cand and (Path(_cand) / "REPORT.md").exists():
        ENV.setdefault("REPO_ROOT", _cand)
        ENV.setdefault("TRANSCRIPT_TAX_REPO", _cand)
        break
_FLEET_LOG = Path("/home/vuos/code/p4/.pi-web/tps-turns.jsonl")
if _FLEET_LOG.exists():
    ENV.setdefault("FLEET_LOG", str(_FLEET_LOG))

LIVE = "https://focalis.cc"
SUITES: list[tuple[str, list[str], str | None]] = [
    ("roi-parity", ["node", str(HERE / "roi-parity.mjs")], None),
    ("audit-report", [sys.executable, str(HERE / "audit-report-test.py")], None),
    ("gate", [sys.executable, str(HERE / "gate-test.py")], None),
    ("roi-browser", [sys.executable, str(HERE / "roi-browser.py")],
     None if LOCAL else f"{LIVE}/audit/"),
    ("preview-parity", [sys.executable, str(HERE / "preview-parity.py")],
     None if LOCAL else f"{LIVE}/audit/preview/"),
    ("deliverable", [sys.executable, str(HERE / "deliverable-browser.py")],
     None if LOCAL else f"{LIVE}/audit/sample/"),
    ("company-pages", [sys.executable, str(HERE / "company-pages.py")],
     "--local" if LOCAL else None),
    ("routes-page", [sys.executable, str(HERE / "routes-page.py")],
     "--local" if LOCAL else None),
    ("funnel-links", [sys.executable, str(HERE / "funnel-links.py")], None),
    ("paper-matrix", [sys.executable, str(HERE / "paper-matrix.py")], None),
    ("matrix-prices", [sys.executable, str(HERE / "matrix-prices.py")], None),
    ("procsplit-claims", [sys.executable, str(HERE / "procsplit-claims.py")], None),
    ("fleet-window", [sys.executable, str(HERE / "fleet-window.py")], None),
    ("bench-claims", [sys.executable, str(HERE / "bench-claims.py")], None),
    ("offer-mirror", [sys.executable, str(HERE / "offer-mirror.py")], None),
    ("sample-repro", [sys.executable, str(HERE / "sample-repro.py")], None),
]

results: list[tuple[str, bool, str]] = []
for name, cmd, arg in SUITES:
    if arg:
        cmd = cmd + [arg]
    print(f"\n{'=' * 72}\n{name}: {' '.join(cmd)}\n{'=' * 72}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=ENV)
    out = (r.stdout + r.stderr).strip().splitlines()
    tail = out[-1] if out else "(no output)"
    for line in out:
        if line.startswith("FAIL"):
            print("  " + line)
    print(f"  -> exit {r.returncode}: {tail}")
    results.append((name, r.returncode == 0, tail))

print("\n" + "=" * 72)
print("SUMMARY" + (" (local artifacts)" if LOCAL else " (live URLs)"))
for name, ok, tail in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name:16} {tail[:90]}")
bad = [n for n, ok, _ in results if not ok]
print(f"\n{len(results) - len(bad)}/{len(results)} suites passed" + (f" — failing: {', '.join(bad)}" if bad else ""))
sys.exit(1 if bad else 0)
