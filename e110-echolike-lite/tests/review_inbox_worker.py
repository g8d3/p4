"""Hosted inbox review: the live multi-tenant Worker, over the public internet.

Two tenants are claimed on the spot; each can only see its own captures. This is
the thing the extension talks to when the user has no server of their own, so it
is checked against the deployed URL, not a mock.

    python3 tests/review_inbox_worker.py [base-url]

Exit code 1 on any failure.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://inbox-lite.echolike.app").rstrip("/")
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"


def dec(key, blob):
    """Read a blob the way the extension's page would. None when it is the wrong key."""
    try:
        plain = AESGCM(key).decrypt(base64.b64decode(blob["iv"]), base64.b64decode(blob["ct"]), None)
        return json.loads(plain).get("text")
    except Exception:
        return None


def seal(key, obj):
    """What the extension does before uploading: AES-256-GCM, blob only."""
    iv = os.urandom(12)
    ct = AESGCM(key).encrypt(iv, json.dumps(obj).encode(), None)
    b64 = lambda b: base64.b64encode(b).decode()
    return {"uid": obj.get("uid"), "iv": b64(iv), "ct": b64(ct)}


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
check("health states the client contract", health.get("min_client_api"), 4)
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

ka, kb = os.urandom(32), os.urandom(32)
code, r = call(
    "/api/likes",
    ta,
    {"items": [seal(ka, {"uid": "a1", "kind": "like", "id": "111", "handle": "nasa", "url": "https://x.com/nasa/status/111", "text": "A only"})]},
)
check("A posts a capture", (code, r.get("received")), (200, 1))

code, r = call(
    "/api/likes",
    tb,
    {"items": [seal(kb, {"uid": "b1", "kind": "bookmark", "id": "222", "handle": "sama", "url": "https://x.com/sama/status/222", "text": "B only"})]},
)
check("B posts a capture", (code, r.get("received")), (200, 1))

code, ra = call("/api/likes")
check("no token is refused", code, 401)

code, ra = call("/api/likes", ta)
sa = json.dumps(ra)
check("A gets its own blob back", (code, len(ra.get("items") or [])), (200, 1))
check("the worker stores no plaintext", "A only" in sa or "nasa" in sa, False)
check("A's blob decrypts with A's key", dec(ka, ra["items"][0]), "A only")
code, rb = call("/api/likes", tb)
check("B gets its own blob back", (code, len(rb.get("items") or [])), (200, 1))
check("B's blob decrypts with B's key", dec(kb, rb["items"][0]), "B only")
check("A's key does not open B's blob", dec(ka, rb["items"][0]), None)
check("tenant ids reported", (ra.get("user"), rb.get("user")), (ua, ub))

# The reader page is static: it must not carry a single secret or capture.
html = call("/")[1]
if isinstance(html, bytes):
    html = html.decode("utf-8", "replace")
check("reader page is served", "My EchoLike inbox" in html, True)
check("reader page holds no capture", "A only" in html or "B only" in html, False)
check("reader page decrypts client-side", "subtle.importKey" in html, True)

code, r = call("/api/likes", "0" * 32)
check("wrong token refused", code, 401)
code, r = call("/api/likes", ta, {"items": "not a list"})
check("bad body rejected", code, 400)
code, r = call("/api/likes", ta, {"items": []})
# An old client (1.1.x) cannot encrypt, so its queue is accepted and flagged rather
# than dropped. A client that announces API 4 must seal, and is refused otherwise.
code, r = call("/api/likes", ta, {"items": [{"uid": "legacy-1", "kind": "like", "handle": "nasa", "text": "from 1.1.x"}]})
check("legacy plaintext is accepted, not lost", (code, r.get("received")), (200, 1))
code, r = call("/api/likes", ta, {"items": [{"uid": "x", "text": "plaintext from a v4 client"}]}, headers={"x-echolike-api": "4"})
check("a v4 client cannot send plaintext", code, 400)
code, r = call("/api/likes", ta)
legacy = [i for i in (r.get("items") or []) if i.get("legacy")]
check("the legacy row is flagged for the reader", len(legacy) >= 1, True)
code, r = call("/api/likes", ta, {"items": []})
check("empty batch accepted", (code, r.get("received")), (200, 0))

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
