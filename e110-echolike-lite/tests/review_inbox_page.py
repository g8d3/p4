"""The hosted reader page: any browser, no extension, key in the URL fragment.

The promise this checks: the server cannot read a capture, yet a visitor opening
`https://…/#t=<token>&k=<key>` sees the list — because decryption happens in that
browser and both secrets ride in the fragment, which never reaches the server.

    python3 tests/review_inbox_page.py [base-url]

Exit code 1 on any failure.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://inbox-lite.echolike.app").rstrip("/")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
TEXT = "decrypted in the reader page"
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


def call(path, token=None, body=None, method=None):
    h = {"content-type": "application/json", "user-agent": UA}
    if token:
        h["authorization"] = "Bearer " + token
    req = urllib.request.Request(
        BASE + path,
        data=None if body is None else json.dumps(body).encode(),
        method=method or ("POST" if body is not None else "GET"),
        headers=h,
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, json.loads(r.read() or b"{}")


b64 = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")  # what the extension emits
key = os.urandom(32)
keycode = b64(key)
iv = os.urandom(12)
item = {
    "uid": "page-1",
    "kind": "like",
    "id": "777",
    "handle": "nasa",
    "url": "https://x.com/nasa/status/777",
    "text": TEXT,
    "clicked_at": "2026-11-11T10:00:00Z",
}
blob = {"uid": "page-1", "iv": b64(iv), "ct": b64(AESGCM(key).encrypt(iv, json.dumps(item).encode(), None))}

code, claim = call("/api/claim", method="POST")
check("claimed a tenant", (code, claim.get("ok")), (200, True))
token = claim["token"]
code, r = call("/api/likes", token, {"items": [blob]})
check("uploaded a blob", (code, r.get("received")), (200, 1))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # 1. No key in the fragment: the page must ask for it, and show nothing.
    page.goto(BASE + "/#t=" + token)
    page.wait_for_timeout(2500)
    check("asks for the recovery code", page.is_visible("#ask"), True)
    check("shows no capture without it", TEXT in page.inner_text("#list"), False)

    # 2. The real link the popup would build: token + key, both in the fragment.
    page.goto(BASE + "/?b=1#t=" + token + "&k=" + keycode)  # a fresh load, like a real visit
    page.wait_for_timeout(3000)
    body = page.inner_text("#list")
    check("decrypts in the reader", TEXT in body, True)
    check("shows the author", "@nasa" in body, True)
    check("shows the kind", "like" in body, True)
    check("fragment is cleared from the address bar", page.evaluate("location.hash"), "")
    check("the server never saw the key", page.evaluate("document.documentElement.outerHTML").count(keycode), 0)

    # 3. A wrong key must say so instead of pretending.
    page2 = browser.new_page()
    page2.goto(BASE + "/?b=2#t=" + token + "&k=" + b64(os.urandom(32)))
    page2.wait_for_timeout(3000)
    check("wrong key reported", "do not decrypt" in page2.inner_text("#status") or "Wrong" in page2.inner_text("#status"), True)
    check("wrong key shows nothing", TEXT in page2.inner_text("#list"), False)

    browser.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
