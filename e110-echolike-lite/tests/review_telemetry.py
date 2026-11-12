"""Diagnostics: what a button did, never what it captured.

Two halves:
  * the endpoint's contract against the live inbox (whitelist, caps, junk dropped);
  * the stored row, read back from D1 — the only way to prove that a client which
    sends extra fields cannot smuggle a capture into the log.

    python3 tests/review_telemetry.py

Exit code 1 on any failure.
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = "https://inbox-lite.echolike.app"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
MARK = "tel-%d" % int(time.time())
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


def post(events):
    req = urllib.request.Request(
        BASE + "/api/telemetry",
        data=json.dumps({"events": events}).encode(),
        method="POST",
        headers={"content-type": "application/json", "user-agent": UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


code, r = post([{"action": "test." + MARK, "ok": False, "code": 409, "ms": 12, "host": "x", "error": "device limit"}])
check("an event is accepted", (code, r.get("stored")), (200, 1))

code, r = post([{"action": "Not An Action!"}, {"action": "ok.action"}])
check("a malformed action is dropped, the good one kept", (code, r.get("stored")), (200, 1))

code, r = post([{"action": "test." + MARK, "text": "SECRET post text", "handle": "nasa", "url": "https://x.com/nasa/status/1"}])
check("extra fields are accepted but not honoured", (code, r.get("stored")), (200, 1))

code, r = post({"events": "nope"})
check("a non-list is refused", code, 400)
code, r = post([{"action": "x"}] * 40)
check("a batch is capped", r.get("stored", 0) <= 20, True)

# Read the rows back from D1: the columns are the whitelist, nothing else.
env = dict(
    __import__("os").environ,
    CLOUDFLARE_API_TOKEN=__import__("os").environ.get("CLOUDFLARE_API_TOKEN")
    or __import__("os").environ.get("CLOUDFLARE_FOCALIS_API_KEY", ""),
)
out = subprocess.run(
    ["wrangler", "d1", "execute", "echolike-inbox", "--remote", "--json", "--command",
     "SELECT * FROM telemetry WHERE action LIKE 'test.%' ORDER BY id DESC LIMIT 5"],
    cwd=str(__import__("pathlib").Path(__file__).resolve().parent.parent / "inbox-worker"),
    capture_output=True, text=True, timeout=180, env=env,
)
if out.returncode != 0:
    print("  note: could not query D1 —", (out.stderr or out.stdout)[-200:])
    print("FAILURES:", failures + ["d1"])
    sys.exit(1)
rows = json.loads(out.stdout)[0]["results"]
check("the rows are there", len(rows) >= 2, True)
cols = sorted(rows[0].keys())
check(
    "only whitelisted columns exist",
    cols,
    ["action", "at", "code", "error", "host", "id", "ip_hash", "ms", "ok", "user_id", "version"],
)
check("no capture text anywhere", any("SECRET post text" in json.dumps(r) for r in rows), False)
check("no handle either", any("nasa" in json.dumps(r) for r in rows), False)
check("the action is recorded", any(MARK in r["action"] for r in rows), True)
check("the error text is recorded", any("device limit" in (r.get("error") or "") for r in rows), True)

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
