"""Two browsers, one X account, one list.

The reported problem: the same X account in two browsers, and switching browsers
hides likes. The cause was the model, not a failure — every install claimed its own
tenant with its own key, and the reader showed one tenant. Now an account reads
every device it has linked, and the reader dedupes the same like captured twice.

Local worker (no real mail, no real quota):

    cd inbox-worker && wrangler dev --port 8788 --local --compatibility-date 2026-10-30
    xvfb-run -a python3 tests/review_two_browsers.py

Exit code 1 on any failure.
"""
import base64
import json
import os
import pathlib
import sys
import uuid

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ids import extension_id  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8788"
EMAIL = "two-%d@example.com" % __import__("random").randint(1000, 9999)
b64 = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


def call(path, token=None, body=None, method=None):
    import urllib.request

    h = {"content-type": "application/json"}
    if token:
        h["authorization"] = "Bearer " + token
    req = urllib.request.Request(
        BASE + path,
        data=None if body is None else json.dumps(body).encode(),
        method=method or ("POST" if body is not None else "GET"),
        headers=h,
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status, json.loads(r.read() or b"{}")


def seal(key, item):
    iv = os.urandom(12)
    return {"uid": item["uid"], "iv": b64(iv), "ct": b64(AESGCM(key).encrypt(iv, json.dumps(item).encode(), None))}


# Two installs of the same person: two tenants, one key (after the account restore).
key = os.urandom(32)
_, a = call("/api/claim", method="POST")
_, b = call("/api/claim", method="POST")
check("two devices claimed", a["user"] != b["user"], True)

# The same like captured in both browsers, plus one unique each.
shared = {"uid": str(uuid.uuid4()), "kind": "like", "id": "777", "handle": "nasa",
          "url": "https://x.com/nasa/status/777", "text": "the same like, twice", "clicked_at": "2026-11-12T00:00:00Z"}
only_a = {"uid": str(uuid.uuid4()), "kind": "like", "id": "888", "handle": "esa",
          "url": "https://x.com/esa/status/888", "text": "only from browser A", "clicked_at": "2026-11-12T00:01:00Z"}
only_b = {"uid": str(uuid.uuid4()), "kind": "bookmark", "id": "999", "handle": "sama",
          "url": "https://x.com/sama/status/999", "text": "only from browser B", "clicked_at": "2026-11-12T00:02:00Z"}
call("/api/likes", a["token"], {"items": [seal(key, shared), seal(key, only_a)]})
call("/api/likes", b["token"], {"items": [seal(key, shared), seal(key, only_b)]})

# One account signs both devices in.
_, start = call("/api/account/start", body={"email": EMAIL})
code = start.get("code") or ""
check("dev code", len(code), 6)
_, va = call("/api/account/verify", a["token"], {"email": EMAIL, "code": code})
_, start2 = call("/api/account/start", body={"email": EMAIL})
_, vb = call("/api/account/verify", b["token"], {"email": EMAIL, "code": start2.get("code")})
atoken = vb.get("atoken") or ""
check("one account, two devices", (va["ok"], vb["ok"]), (True, True))

code_, acc = call("/api/account/likes", atoken)
check("the account reads both devices", (code_, acc.get("total")), (200, 4))
check("two tenants listed", len(acc.get("tenants") or []), 2)

plain = []
for blob in acc["items"]:
    data = AESGCM(key).decrypt(base64.urlsafe_b64decode(blob["iv"] + "=="), base64.urlsafe_b64decode(blob["ct"] + "=="), None)
    plain.append(json.loads(data))
check("every capture decrypts with the account key", len(plain), 4)

# A device token still only sees its own tenant: the account is the wider lens.
_, dev_a = call("/api/likes", a["token"])
check("a single device still sees only itself", len(dev_a["items"]), 2)

# The reader in a real browser: seeded as a signed-in device, shows one row per like.
prof = pathlib.Path(__import__("tempfile").mkdtemp(prefix="echolike-lite-two-"))
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        str(prof), headless=False,
        args=[f"--disable-extensions-except={ROOT / 'extension'}", f"--load-extension={ROOT / 'extension'}", "--no-first-run"],
    )
    try:
        page = ctx.new_page()
        page.on("pageerror", lambda e: print("PAGEERROR", str(e)[:200]))
        page.goto(f"chrome-extension://{extension_id()}/app.html#inbox")
        page.wait_for_timeout(400)
        page.evaluate(
            """(s) => chrome.storage.local.set({url: s.url, token: s.token, accountToken: s.atoken,
                 accountEmail: s.email, key: s.key})""",
            {"url": BASE, "token": b["token"], "atoken": atoken, "email": EMAIL, "key": b64(key)},
        )
        page.reload()
        page.wait_for_timeout(3000)
        rows = page.query_selector_all("#list div")
        check("the reader lists the account, not one device", len(rows), 3)
        text = page.inner_text("#list")
        check("it says it is the account", "in my account" in page.inner_text("#status"), True)
        check("browser A's capture is visible", "only from browser A" in text, True)
        check("browser B's capture is visible", "only from browser B" in text, True)
        check("the shared like appears once", text.count("the same like, twice"), 1)
    finally:
        ctx.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
