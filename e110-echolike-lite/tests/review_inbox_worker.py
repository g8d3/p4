"""Hosted inbox review: the live multi-tenant Worker, over the public internet.

Two tenants are claimed on the spot; each can only see its own captures. This is
the thing the extension talks to when the user has no server of their own, so it
is checked against the deployed URL, not a mock.

    python3 tests/review_inbox_worker.py [base-url]

Exit code 1 on any failure.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://inbox-lite.echolike.app").rstrip("/")
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"


def call(path, token=None, body=None, method=None, headers=None):
    # Cloudflare answers the bare python-urllib UA with 403; the extension talks
    # with a browser UA, so the test does too.
    h = {"content-type": "application/json", "user-agent": UA}
    if token:
        h["authorization"] = "Bearer " + token
    h.update(headers or {})
    req = urllib.request.Request(
        BASE + path,
        data=None if body is None else json.dumps(body).encode(),
        method=method or ("POST" if body is not None else "GET"),
        headers=h,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
            try:
                return r.status, json.loads(raw or b"{}")
            except ValueError:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw or b"{}")
        except ValueError:
            return e.code, raw


code, health = call("/api/health")
check("health ok", (code, health.get("ok")), (200, True))
check("health advertises open claim", health.get("claim"), "open")
check("free quota advertised", health.get("free_per_month", 0) > 0, True)

# Two separate tenants, as two separate installs would be.
code, a = call("/api/claim", method="POST")
check("tenant A claimed", (code, a.get("ok")), (200, True))
code, b = call("/api/claim", method="POST")
check("tenant B claimed", (code, b.get("ok")), (200, True))
ta, tb, ua, ub = a.get("token"), b.get("token"), a.get("user"), b.get("user")
check("tokens are 32 hex", len(ta or "") == 32 and len(tb or "") == 32, True)
check("tokens differ", ta != tb, True)
check("tenants differ", ua != ub, True)

code, r = call(
    "/api/likes",
    ta,
    {"items": [{"uid": "a1", "kind": "like", "id": "111", "handle": "nasa", "url": "https://x.com/nasa/status/111", "text": "A only"}]},
)
check("A posts a capture", (code, r.get("received")), (200, 1))

code, r = call(
    "/api/likes",
    tb,
    {"items": [{"uid": "b1", "kind": "bookmark", "id": "222", "handle": "sama", "url": "https://x.com/sama/status/222", "text": "B only"}]},
)
check("B posts a capture", (code, r.get("received")), (200, 1))

code, ra = call("/api/likes")
check("no token is refused", code, 401)

code, ra = call("/api/likes", ta)
sa = json.dumps(ra)
check("A reads its own", (code, "A only" in sa), (200, True))
check("A cannot see B", "B only" in sa, False)
code, rb = call("/api/likes", tb)
sb = json.dumps(rb)
check("B cannot see A", "A only" in sb, False)
check("tenant ids reported", (ra.get("user"), rb.get("user")), (ua, ub))

# The readable page: token in the query is the only key, and it is tenant-scoped.
html = call("/?t=" + ta)[1]
if isinstance(html, bytes):
    html = html.decode("utf-8", "replace")
check("inbox page shows A's capture", "A only" in html, True)
check("inbox page hides B's", "B only" in html, False)
nobody = call("/?t=" + "0" * 32)[1]
if isinstance(nobody, bytes):
    nobody = nobody.decode("utf-8", "replace")
check("page without a key shows nothing", "A only" in nobody or "B only" in nobody, False)

code, r = call("/api/likes", "0" * 32)
check("wrong token refused", code, 401)
code, r = call("/api/likes", ta, {"items": "not a list"})
check("bad body rejected", code, 400)
code, r = call("/api/likes", ta, {"items": []})
check("empty batch accepted", (code, r.get("received")), (200, 0))

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
