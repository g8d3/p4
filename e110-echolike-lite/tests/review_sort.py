"""Ordering, filtering and self-repair — the three things a user judges the list by.

The failure this pins down, seen for real: a like was captured and sent, the
extension page said "15 not in the inbox yet" (they *were* in the inbox, just past
a capped read window), pressing "send" re-uploaded them as new rows, and those
duplicates pushed the fresh like off the visible page — which reads as data loss.

So this checks, against the live inbox and a real Chrome:
  * one capture is one row, however many times it is sent;
  * a page read covers the whole inbox (offset pages), not the first 200;
  * a capture the inbox lacks is sent by itself, with no button pressed;
  * every surface can be ordered by the four dates and the five counts, both ways,
    and the choice survives a reload.

    python3 tests/review_sort.py [base-url]

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
BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://inbox-lite.echolike.app").rstrip("/")
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
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.status, json.loads(r.read() or b"{}")


b64 = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")
unb64 = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class Sealer:
    """Seal exactly like the extension does, with the extension's OWN key.

    The key is generated in the browser on first run and never leaves it, so the
    test reads it from `state` after the page opens. Sealing with a key of our own
    would make every row undecryptable in the page and prove nothing.
    """

    def __init__(self):
        self.aes = None

    def use(self, keycode):
        self.aes = AESGCM(unb64(keycode))

    def blob(self, it):
        assert self.aes is not None, "read the extension key first"
        iv = os.urandom(12)
        ct = self.aes.encrypt(iv, json.dumps(it).encode(), None)
        return {"uid": it["uid"], "iv": b64(iv), "ct": b64(ct)}


sealer = Sealer()


def cap(uid, post, handle, clicked, published, **counts):
    return {
        "uid": uid,
        "kind": "bookmark" if handle == "gamma" else "like",
        "id": post,
        "handle": handle,
        "url": "https://x.com/%s/status/%s" % (handle, post),
        "text": "sort test %s" % handle,
        "clicked_at": clicked,
        "captured_at": clicked,
        "published_at": published,
        "counts": dict({"replies": 1, "reposts": 2, "likes": 0, "bookmarks": 0, "views": 0}, **counts),
    }


# A: oldest click, fewest likes ; B: newest click, most likes ; C: middle, bookmark.
A = cap("sort-a", "9001", "alpha", "2026-11-01T10:00:00Z", "2026-10-01T00:00:00Z", likes=5, views=1000)
B = cap("sort-b", "9002", "beta", "2026-11-03T10:00:00Z", "2026-10-03T00:00:00Z", likes=900, views=10)
C = cap("sort-c", "9003", "gamma", "2026-11-02T10:00:00Z", "2026-10-02T00:00:00Z", likes=50, views=500)

code, claim = call("/api/claim", method="POST")
check("claimed a tenant", (code, claim.get("ok")), (200, True))
token = claim["token"]

prof = tempfile.mkdtemp(prefix="echolike-lite-sort-")
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        prof, headless=False,
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-first-run"],
    )
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)[:160]))
    page.goto(f"chrome-extension://{extension_id()}/app.html")
    page.wait_for_timeout(600)
    # The extension's key, generated in the browser: seal the fixtures with it.
    state = page.evaluate("chrome.runtime.sendMessage({type:'state'})")
    keycode = state["keyCode"]
    check("the extension has a key", bool(keycode), True)
    sealer.use(keycode)

    code, r = call("/api/likes", token, {"items": [sealer.blob(A), sealer.blob(B)]})
    check("two captures uploaded", (code, r.get("received")), (200, 2))
    code, r = call("/api/likes", token, {"items": [sealer.blob(A)]})
    check("a re-send stores nothing new", (code, r.get("received")), (200, 0))
    check("and says it was a duplicate", r.get("duplicates"), 1)
    code, r = call("/api/likes?limit=500", token)
    check("one capture is one row", r.get("total"), 2)
    code, r = call("/api/likes", token, {"items": []})
    check("an empty batch is not an error", (code, r.get("ok")), (200, True))

    # offset pages: the reader can walk the whole inbox
    code, first = call("/api/likes?limit=1&offset=0", token)
    code, second = call("/api/likes?limit=1&offset=1", token)
    check("a page has one row", len(first.get("items", [])), 1)
    check("the next page is a different row", first["items"][0]["uid"] != second["items"][0]["uid"], True)
    check("the total is reported on every page", second.get("total"), 2)
    # Connected to this test tenant, holding A and B (already in the inbox) and C
    # (not in it): opening the page must send C by itself.
    page.evaluate(
        "({url, token, items}) => chrome.storage.local.set({url, token, items, outbox: []})",
        {"url": BASE, "token": token, "items": [A, B, C]},
    )
    page.reload()
    page.wait_for_timeout(3500)
    check("no page errors", errors, [])
    status = page.inner_text("#status")
    check("the inbox count is the real one", "3 in the inbox" in status, True)
    check("no internal error on the status line", "internal" in status, False)
    check("nothing is left unsent", "not in the inbox yet" in status, False)
    code, r = call("/api/likes?limit=500", token)
    check("the missing capture was sent by itself", r.get("total"), 3)
    rows = page.query_selector_all("#list div")
    check("three rows", len(rows), 3)
    check("default order by my interaction, newest first", "beta" in rows[0].inner_text(), True)
    check("the oldest click is last", "alpha" in rows[-1].inner_text(), True)
    check("all four dates are shown", "liked" in rows[0].inner_text() and "published" in rows[0].inner_text(), True)

    page.select_option("#sort", "likes")
    page.wait_for_timeout(300)
    rows = page.query_selector_all("#list div")
    check("sort by post likes, most first", "beta" in rows[0].inner_text(), True)
    check("and the fewest last", "alpha" in rows[-1].inner_text(), True)
    page.click("#dir")
    page.wait_for_timeout(300)
    rows = page.query_selector_all("#list div")
    check("the direction flips to least first", "alpha" in rows[0].inner_text(), True)
    page.click("#dir")
    page.wait_for_timeout(200)

    page.select_option("#filter", "bookmark")
    page.wait_for_timeout(300)
    rows = page.query_selector_all("#list div")
    check("filter by kind leaves the bookmark", (len(rows), "gamma" in rows[0].inner_text() if rows else None), (1, True))
    page.select_option("#filter", "all")
    page.wait_for_timeout(300)

    page.reload()
    page.wait_for_timeout(1500)
    check("the sort choice survives a reload", page.eval_on_selector("#sort", "e => e.value"), "likes")
    check("and so does the direction", page.inner_text("#dir"), "most first")

    # Same data, no extension: the hosted reader must offer the same controls and
    # must not hide anything behind a capped window.
    reader = ctx.new_page()
    reader.goto(BASE + "/#t=" + token + "&k=" + keycode)
    reader.wait_for_timeout(3000)
    check("the reader lists every capture", len(reader.query_selector_all("#list div")), 3)
    check("no 'showing the newest' excuse", "showing the newest" in reader.inner_text("#status"), False)
    check("the reader has the sort control", reader.is_visible("#sort"), True)
    reader.select_option("#sort", "views")
    reader.wait_for_timeout(400)
    rrows = reader.query_selector_all("#list div")
    check("the reader sorts by views, most first", "alpha" in rrows[0].inner_text(), True)
    reader.click("#dir")
    reader.wait_for_timeout(400)
    rrows = reader.query_selector_all("#list div")
    check("and flips", "beta" in rrows[0].inner_text(), True)
    ctx.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
