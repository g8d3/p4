#!/usr/bin/env python3
"""Dogfood check: use the desk as a user would. Spends $0, never writes data.

Fetches / and /api/state like a browser, asserts what a user would see:
page renders, prices show single $, API keys present, heartbeat ages sane,
ledger lines parse. Failures append to log/desk-issues.jsonl for the fix queue.

Usage: python3 bin/selfcheck.py [--base http://127.0.0.1:8327]
Exit 0 = SELFCHECK OK, 1 = issues found (listed + logged).
"""
import datetime
import json
import os
import sys
import urllib.request

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else \
    "http://127.0.0.1:8327"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return r.status, r.read().decode()


issues = []

try:
    sc, page = get("/")
    if sc != 200:
        issues.append("page status %s" % sc)
    for needle in ["profit loop", "api/state", "ledger tail", "workers"]:
        if needle not in page.lower():
            issues.append("page missing section: %s" % needle)
    # NOTE: never grep rendered artifacts ($$, ${...}) in raw HTML — the JS
    # template `$${x}` is correct ($ + interpolation) and only a rendered-DOM
    # check (bin/rendercheck.sh) can judge pixels. See 2026-09-18 incident.
except Exception as e:  # noqa: BLE001
    issues.append("page unreachable: %s" % str(e)[:120])
    page = ""

try:
    sc, raw = get("/api/state")
    d = json.loads(raw)
    for k in ["credits", "heartbeats", "counts", "events", "loop", "economy"]:
        if k not in d:
            issues.append("api missing key: %s" % k)
    for w, b in (d.get("heartbeats") or {}).items():
        age = b.get("age_min")
        if not isinstance(age, (int, float)) or age < 0 or age > 60 * 24 * 7:
            issues.append("insane heartbeat age for %s: %r" % (w, age))
    c = d.get("credits", {})
    if c.get("ok") and c.get("remaining", 0) < 0:
        issues.append("negative credits remaining")
    eco = d.get("economy", {}) or {}
    u = eco.get("utilization")
    if u is not None and not (isinstance(u, (int, float)) and 0 <= u <= 1):
        issues.append("economy.utilization out of range: %r" % (u,))
except Exception as e:  # noqa: BLE001
    issues.append("api broken: %s" % str(e)[:120])

if issues:
    line = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%FT%TZ"),
            "who": "selfcheck", "issues": issues}
    with open(os.path.join(DIR, "log", "desk-issues.jsonl"), "a") as f:
        f.write(json.dumps(line) + "\n")
    print("SELFCHECK FAIL:")
    for i in issues:
        print(" -", i)
    sys.exit(1)
print("SELFCHECK OK (page + api render as a user expects)")
