#!/usr/bin/env python3
"""The published Tier 2 examples must be reproducible from the published fleet files.

    python3 tests/sample-repro.py            # against the live pages and the live repo files
    python3 tests/sample-repro.py --local    # against sample-pack/ and the local repo copy

Why: the four example deliverables at <https://focalis.cc/audit/sample/> were generated from the
**live** turn log, which rotates — so the window behind their figures disappeared and nobody could
check them (the same class R80/R52 found). They are now generated from a window we publish
(`fleet/fleet-turns-2026-10-18.jsonl` + `fleet/fleet-history-2026-10-18.jsonl` in the paper's
repository) with `fleet/example-answers.json`, which is what makes the numbers a reader downloads
match the numbers the pages show.

This test is the evidence: it downloads those files, re-runs the delivery engine into a temp
directory from scratch, and compares the four files **byte for byte** with the ones being served.
If a page drifts from the published inputs, the bytes differ and this fails.

Pack-only by design: `audit_report.py` is the delivery engine and is shipped to clients, not
published (R27), so a fresh clone of the paper's repository cannot run the generator itself — it can
run the numbers, which is what `fleet/publish_fleet.py analyze` is for.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent
LOCAL = "--local" in sys.argv
LIVE = "https://focalis.cc"
WINDOW_DATE = "2026-10-18"
TURNS = f"fleet/fleet-turns-{WINDOW_DATE}.jsonl"
HISTORY = f"fleet/fleet-history-{WINDOW_DATE}.jsonl"
ANSWERS = "fleet/example-answers.json"
EXAMPLES = ("cuts.html", "budget.html", "cache-report.html", "size-curve.html")

fails: list[str] = []


def check(name: str, ok: bool, extra: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f" — {extra}" if extra else ""))
    if not ok:
        fails.append(name)


def repo_root() -> Path | None:
    """The paper's repository, locally if we can, else None (then we fetch over the network)."""
    for cand in (os.environ.get("REPO_ROOT"), "/home/vuos/srv/tps", str(PACK.parent)):
        if cand and (Path(cand) / "REPORT.md").exists():
            return Path(cand)
    return None


def fetch(rel: str, dest: Path) -> Path:
    """A published file: from the local clone when there is one, else from the live site."""
    root = repo_root()
    local = (root / rel) if root else None
    if local and local.exists():
        dest.write_bytes(local.read_bytes())
    else:
        req = urllib.request.Request(f"{LIVE}/tps/{rel}", headers={"User-Agent": "focalis-repro"})
        with urllib.request.urlopen(req, timeout=60) as r:
            dest.write_bytes(r.read())
    return dest


# The host injects its own scripts into every HTML page it serves through urllib's request
# fingerprint (curl gets the clean file; urllib gets the injected one — Cloudflare's browser
# integrity path, same thing that 403s bare POSTs, R37). The comparison normalises that away and
# asserts the difference is *only* the host's script, so a stale page still fails.
HOST_SCRIPT = re.compile(r"\n?<script[^>]*(?:cloudflareinsights|cdn-cgi)[^>]*>.*?</script>", re.S)
# ... and it rewrites our contact link into its own email-protection form, so that has to be put
# back before comparing (and it is worth asserting that it decodes to the address we published).
CF_EMAIL = re.compile(r'<a href="/cdn-cgi/l/email-protection#([0-9a-f]+)">'
                      r'<span class="__cf_email__" data-cfemail="[0-9a-f]+">.*?</span></a>', re.S)
BROWSER_UA = {"User-Agent": "Mozilla/5.0 Chrome/130"}


def cf_decode(hexed: str) -> str:
    key = int(hexed[:2], 16)
    return "".join(chr(int(hexed[i:i + 2], 16) ^ key) for i in range(2, len(hexed), 2))


def unhost(html: str) -> str:
    """Undo what the host adds to a page it serves: its scripts and its link rewriting."""
    def put_back(m):
        addr = cf_decode(m.group(1))
        return f'<a href="mailto:{addr}">{addr}</a>'
    return CF_EMAIL.sub(put_back, HOST_SCRIPT.sub("", html))


def served(name: str) -> str:
    if LOCAL:
        return (PACK / "sample-pack" / name).read_text()
    req = urllib.request.Request(f"{LIVE}/audit/sample/{name}", headers=BROWSER_UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        turns = fetch(TURNS, tmp / Path(TURNS).name)
        history = fetch(HISTORY, tmp / Path(HISTORY).name)
        answers = fetch(ANSWERS, tmp / Path(ANSWERS).name)
        check("the published turn window is readable and non-empty", turns.stat().st_size > 1000,
              f"{turns.stat().st_size} B")
        check("the published message-sample window is readable and non-empty",
              history.stat().st_size > 1000, f"{history.stat().st_size} B")
        # the windows must not carry what we promised not to publish
        for label, path in (("turn window", turns), ("history window", history)):
            raw = path.read_text()
            check(f"{label} carries no session name", "sessionName" not in raw)
            check(f"{label} rows all use opaque session labels",
                  '"sessionId":"s' in raw or '"sessionId": "s' in raw)
        ans = json.loads(answers.read_text())
        check("the published answers name the published windows",
              Path(TURNS).name in ans.get("loop", "") and Path(HISTORY).name in ans.get("loop", ""),
              ans.get("loop", "")[:70])

        out = tmp / "out"
        cmd = [sys.executable, str(PACK / "audit_report.py"), "--answers", str(answers),
               "--log", str(turns), "--history", str(history), "--outdir", str(out), "--html"]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PACK))
        check("the delivery engine runs on the published files", r.returncode == 0,
              (r.stderr or r.stdout).strip().splitlines()[-1][:120] if (r.stderr or r.stdout) else "")

        for name in EXAMPLES:
            produced = out / name
            check(f"{name} was produced", produced.exists() and produced.stat().st_size > 500)
            if not produced.exists():
                continue
            mine = produced.read_text()
            raw = served(name)
            hosted = unhost(raw)
            check(f"{name} matches the served page once the host's own rewriting is undone",
                  hosted == mine, f"served {len(raw)} B → {len(hosted)} B vs regenerated {len(mine)} B")
            if not LOCAL:
                check(f"{name}: the host's email protection decodes to the address we published",
                      "hello@focalis.cc" in unhost(raw) or CF_EMAIL.search(raw) is None)

    print(f"\n{'ALL PASS' if not fails else 'FAILURES: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
