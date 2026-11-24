"""The hosted reader page: any browser, no extension, key in the URL fragment.

The promise this checks: the server cannot read a capture, yet a visitor opening
`https://…/#t=<token>&k=<key>` sees the list — because decryption happens in that
browser and both secrets ride in the fragment, which never reaches the server.

It also checks that the page never dead-ends: a bare URL explains how to connect
and offers a field, a dead link says so and asks for a fresh code, a pasted code
opens the list, and the link is remembered for the next visit.

    python3 tests/review_inbox_page.py [base-url]

Exit code 1 on any failure.
"""
import base64
import json
import os
import sys
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

# "Your inbox code" exactly as the extension builds it: base64url of {u,t,k}.
pair_code = b64(json.dumps({"u": BASE, "t": token, "k": keycode}).encode())


def fresh(browser):
    ctx = browser.new_context()
    return ctx, ctx.new_page()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # 1. Bare URL, nothing stored: explain how to connect, never "not valid".
    ctx, page = fresh(browser)
    page.goto(BASE + "/?bare=1")
    page.wait_for_timeout(1500)
    body = page.inner_text("#status") + " " + page.inner_text("#gate")
    check("bare URL shows the gate", page.is_visible("#gate"), True)
    check("bare URL explains the page", "needs the link" in body or "not a login" in body, True)
    check("bare URL is not an error", "not valid" in body, False)
    ctx.close()

    # 2. The real link the extension builds: token + key, both in the fragment.
    ctx, page = fresh(browser)
    page.goto(BASE + "/?b=1#t=" + token + "&k=" + keycode)
    page.wait_for_timeout(4500)
    body = page.inner_text("#list")
    check("decrypts in the reader", TEXT in body, True)
    check("shows the author", "@nasa" in body, True)
    check("shows the kind", "like" in body, True)
    check("fragment is cleared from the address bar", page.evaluate("location.hash"), "")
    check("the server never saw the key", page.evaluate("document.documentElement.outerHTML").count(keycode), 0)
    check("says the link is saved here", "saved on this browser" in page.inner_text("#linkstate"), True)

    # 3. Same browser, bare URL: the saved link is reused instead of asking again.
    page.goto(BASE + "/?b=3")
    page.wait_for_timeout(4500)
    check("bare URL after a real visit still shows the list", TEXT in page.inner_text("#list"), True)
    ctx.close()

    # 4. A dead token (the incident): say it, stop replaying it, offer a fresh code.
    ctx, page = fresh(browser)
    page.goto(BASE + "/?b=4#t=" + "f" * 32 + "&k=" + keycode)
    page.wait_for_timeout(4000)
    body = page.inner_text("#status") + " " + page.inner_text("#gate")
    check("dead token is explained", "no longer valid" in body, True)
    check("dead token offers the code field", page.is_visible("#gatecode"), True)
    check("dead token is cleared from storage", page.evaluate("localStorage.getItem('el_token')"), None)
    # The one action that can work: paste the code from a phone that still opens it.
    page.fill("#gatecode", pair_code)
    page.click("#gateuse")
    page.wait_for_timeout(4500)
    check("pasted code opens the list", TEXT in page.inner_text("#list"), True)
    check("pasted code is remembered", page.evaluate("localStorage.getItem('el_token')"), token)
    ctx.close()

    # 5. A wrong key must say so instead of pretending.
    ctx, page = fresh(browser)
    page.goto(BASE + "/?b=5#t=" + token + "&k=" + b64(os.urandom(32)))
    page.wait_for_timeout(4500)
    check("wrong key reported", "does not open anything" in page.inner_text("#status"), True)
    check("wrong key shows nothing", TEXT in page.inner_text("#list"), False)
    ctx.close()

    # 6. A code for another inbox is named, never sent there.
    ctx, page = fresh(browser)
    page.goto(BASE + "/?b=6")
    page.wait_for_timeout(1200)
    other = b64(json.dumps({"u": "https://example.com", "t": token, "k": keycode}).encode())
    page.fill("#gatecode", other)
    page.click("#gateuse")
    page.wait_for_timeout(800)
    check("foreign code is named", "example.com" in page.inner_text("#gateerr"), True)
    ctx.close()

    browser.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
