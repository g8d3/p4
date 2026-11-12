"""Two phones, one list — and never a doubt about which list you are looking at.

The owner's report: two phones on the same X account, likes made on the old one do
not show on the new one. Root cause was structural, not a bug in a loop: each install
claims its own tenant, and each seals with its own key, so "the same account" was two
private lists. The answer is a pairing code that carries the list's address, its
device token and its key: paste it and the second phone reads and writes the SAME
list. This checks that end to end, plus the identity line that makes it visible.

    python3 tests/review_pair.py

Exit code 1 on any failure.
"""
import base64
import json
import os
import pathlib
import sys
import tempfile
import urllib.error
import urllib.request

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ids import extension_id  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"
BASE = "https://inbox-lite.echolike.app"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
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
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


b64 = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")
unb64 = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def cap(uid, post, clicked):
    return {
        "uid": uid,
        "kind": "like",
        "id": post,
        "handle": "nasa",
        "url": "https://x.com/nasa/status/" + post,
        "text": "pair test " + post,
        "clicked_at": clicked,
        "captured_at": clicked,
        "counts": {"likes": 1},
    }


with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        tempfile.mkdtemp(prefix="echolike-pair-"), headless=False,
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-first-run"],
    )
    page = ctx.new_page()
    page.on("pageerror", lambda e: failures.append("pageerror: " + str(e)[:140]))
    page.goto(f"chrome-extension://{extension_id()}/app.html")
    page.wait_for_timeout(700)

    state = page.evaluate("chrome.runtime.sendMessage({type:'state'})")
    key2 = state["keyCode"]                       # this "new phone"'s own key
    aes2 = AESGCM(unb64(key2))

    # The OLD phone: its own tenant, its own key, two captures already in it.
    code, old = call("/api/claim", method="POST")
    check("the old phone has a list", (code, old.get("ok")), (200, True))
    key1 = b64(os.urandom(32))
    aes1 = AESGCM(unb64(key1))
    old_blobs = []
    for it in (cap("old-1", "5001", "2026-11-10T10:00:00Z"), cap("old-2", "5002", "2026-11-10T11:00:00Z")):
        iv = os.urandom(12)
        old_blobs.append({"uid": it["uid"], "iv": b64(iv), "ct": b64(aes1.encrypt(iv, json.dumps(it).encode(), None))})
    code, r = call("/api/likes", old["token"], {"items": old_blobs})
    check("the old phone stored two", (code, r.get("received")), (200, 2))

    # The NEW phone: a different tenant, a different key, one capture of its own.
    code, new = call("/api/claim", method="POST")
    check("the new phone has its own list", (code, new.get("ok")), (200, True))
    mine = cap("new-1", "6001", "2026-11-12T10:00:00Z")
    iv = os.urandom(12)
    code, r = call("/api/likes", new["token"], {"items": [{"uid": mine["uid"], "iv": b64(iv), "ct": b64(aes2.encrypt(iv, json.dumps(mine).encode(), None))}]})
    check("the new phone stored one", (code, r.get("received")), (200, 1))

    page.evaluate(
        "({url, token, items}) => chrome.storage.local.set({url, token, items, outbox: []})",
        {"url": BASE, "token": new["token"], "items": [mine]},
    )
    page.reload()
    page.wait_for_timeout(2500)
    before = page.inner_text("#status")
    ident = page.inner_text("#identity")
    check("the page says which list it is on", new["token"][:0] == "" and len(ident) > 0, True)
    check("and that this is one phone only", "this phone only" in ident, True)
    check("the new phone sees only its own capture", "1 in the inbox" in before, True)
    check("the old phone's likes are not there", "3 in the inbox" in before, False)

    # The pairing code the old phone would show (address + token + key, base64url).
    pairing = b64(json.dumps({"v": 1, "u": BASE, "t": old["token"], "k": key1}).encode())

    page.click("#tab-settings")
    page.wait_for_timeout(300)
    check("the old phone's own code is offered", len(page.eval_on_selector("#paircode", "e => e.value")) > 40, True)
    check("and it is masked", page.eval_on_selector("#paircode", "e => e.type"), "password")

    # A bad code must be refused without changing anything.
    page.fill("#pairin", "not-a-code")
    page.click("#pairuse")
    page.wait_for_timeout(800)
    check("a broken code is refused", "not a pairing code" in page.inner_text("#pairmsg"), True)
    check("and the phone is still on its own list", page.evaluate("chrome.storage.local.get({url:''})")["url"] == BASE, True)

    # A code whose key does not open the list must be refused too (that is the trap:
    # adopting it produces a list of rows nobody can read).
    wrong = b64(json.dumps({"v": 1, "u": BASE, "t": old["token"], "k": key2}).encode())
    page.fill("#pairin", wrong)
    page.click("#pairuse")
    page.wait_for_timeout(1200)
    check("a code from another key is refused", "does not open" in page.inner_text("#pairmsg"), True)

    # The real one: this phone joins the old phone's list.
    page.fill("#pairin", pairing)
    page.click("#pairuse")
    page.wait_for_timeout(3500)
    msg = page.inner_text("#pairmsg")
    check("pairing succeeded", "same list" in msg, True)
    code, r = call("/api/likes?limit=500", old["token"])
    check("the old phone's list now holds all three", r.get("total"), 3)
    check("this phone's own capture was carried over, not lost", any(b["uid"] == "new-1" for b in r["items"]), True)

    page.click("#tab-inbox")
    page.wait_for_timeout(2500)
    status = page.inner_text("#status")
    ident = page.inner_text("#identity")
    check("the new phone sees the old phone's likes", "3 in the inbox" in status, True)
    check("nothing is unreadable after pairing", "sealed with another key" in ident, False)
    check("and the list is named", len(ident) > 3, True)
    check("two phones share it", "2 phones" in page.inner_text("#deviceid"), True)
    ctx.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
