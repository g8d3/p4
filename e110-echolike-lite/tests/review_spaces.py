"""Shared spaces: the collaborative unit, with invitations that die.

The design the owner asked for, and the reason the pairing code was not enough: a
permanent shared secret cannot be rotated and cannot be revoked one person at a time.
A space is a list several people write to; joining is by a **one-time invite that
expires**; the owner can remove a member; and because every member's rows are decrypted
locally with the same space key, each card can say how many people in the space saved
the same post — the network's way of finding itself, with no profile and nothing about
the post sent to the server.

    python3 tests/review_spaces.py

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
from tenant import tenant as get_tenant  # noqa: E402

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

# The same post, saved by both people: the point of a space is seeing that.
POST = {
    "kind": "like",
    "id": "777",
    "handle": "nasa",
    "author_name": "NASA",
    "url": "https://x.com/nasa/status/777",
    "text": "Same post, two people, one space.",
    "clicked_at": "2026-11-12T10:00:00Z",
    "captured_at": "2026-11-12T10:00:01Z",
    "published_at": "2026-11-11T22:00:00Z",
    "counts": {"replies": 5, "reposts": 4, "likes": 76, "bookmarks": 2, "views": 2100},
}

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        tempfile.mkdtemp(prefix="echolike-spaces-"), headless=False,
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-first-run"],
    )
    page = ctx.new_page()
    page.on("pageerror", lambda e: failures.append("pageerror: " + str(e)[:140]))
    page.goto(f"chrome-extension://{extension_id()}/app.html#spaces")
    page.wait_for_timeout(800)

    me = get_tenant("spaces-owner")
    mine = dict(POST, uid="mine-1", source="like", page="/home")
    page.evaluate(
        "({url, token, items}) => chrome.storage.local.set({url, token, items, outbox: []})",
        {"url": BASE, "token": me["token"], "items": [mine]},
    )
    page.reload()
    page.wait_for_timeout(1500)
    check("the spaces tab is there", page.get_attribute("#tab-spaces", "aria-selected"), "true")
    check("the three boxes are numbered", page.eval_on_selector_all("#panel-spaces [data-section]", "els => els.map(e => e.dataset.section)"), ["P12", "P13", "P14", "P15"])

    # 1. Create a space from the UI.
    page.fill("#spacename", "trip to the moon")
    page.click("#spacecreate")
    page.wait_for_timeout(1800)
    check("the space was created", "Created" in page.inner_text("#spacenew"), True)
    check("and listed", "trip to the moon" in page.inner_text("#spacelist"), True)

    # 2. Invite: one code, from the UI, and it says how long it lives.
    page.click('#spacelist [data-what="invite"]')
    page.wait_for_timeout(1800)
    code_value = page.eval_on_selector('#spacelist [data-space-msg] input', "e => e.value")
    check("an invite code was produced", len(code_value) > 60, True)
    check("and it says it expires", "expires" in page.inner_text("#spacelist [data-space-msg]"), True)
    inv = json.loads(unb64(code_value))
    check("the code carries the space, a token and the key", sorted(k for k in inv if k in ("s", "t", "k", "u")), ["k", "s", "t", "u"])
    check("the token is not the key", inv["t"] != inv["k"], True)

    # 3. Somebody else joins with it.
    other = get_tenant("spaces-member")
    code, joined = call("/api/spaces/" + inv["s"] + "/join", other["token"], {"token": inv["t"]})
    check("the invite works once", (code, joined.get("ok")), (200, True))
    code, again = call("/api/spaces/" + inv["s"] + "/join", other["token"], {"token": inv["t"]})
    check("and a second use is refused", code, 409)
    code, again = call("/api/spaces/" + inv["s"] + "/join", other["token"], {"token": "0" * 32})
    check("a made-up token is refused", code, 404)

    # 4. The second person saves the SAME post into the space (sealed with the space key).
    aes = AESGCM(unb64(inv["k"]))
    iv = os.urandom(12)
    blob = {"uid": "theirs-1", "iv": b64(iv), "ct": b64(aes.encrypt(iv, json.dumps(dict(POST, uid="theirs-1")).encode(), None))}
    code, r = call("/api/spaces/" + inv["s"] + "/likes", other["token"], {"items": [blob]})
    check("their capture went into the space", (code, r.get("received")), (200, 1))

    # 5. The owner shares their own captures, then opens the space.
    page.click('#spacelist [data-what="share"]')
    page.wait_for_timeout(2500)
    check("sharing reported what it did", "shared" in page.inner_text('#spacelist [data-space-msg]'), True)
    page.click('#spacelist [data-what="open"]')
    page.wait_for_timeout(2500)
    rows = page.query_selector_all("#spacelistitems .cap")
    check("the space shows the post once, not twice", len(rows), 1)
    body = page.inner_text("#spacelistitems")
    check("both people are counted on the card", "saved by 2 people here" in body, True)
    check("and the other person is named by id", "also saved by" in body, True)
    check("two members are reported", "2 members" in page.inner_text("#spacehead"), True)
    check("the card keeps X's shape", page.eval_on_selector_all("#spacelistitems .cap:first-child .head .av", "els => els.length"), 1)
    check("with five action cells", page.eval_on_selector_all("#spacelistitems .cap:first-child .stats span", "els => els.length"), 5)
    check("our four dates are still there", "published" in body and "arrived" in body, True)

    # 6. A stranger cannot read the space, and the owner can cut the member off.
    stranger = get_tenant("spaces-stranger")
    code, denied = call("/api/spaces/" + inv["s"] + "/likes", stranger["token"])
    check("an outsider is refused", code, 403)
    code, removed = call("/api/spaces/" + inv["s"] + "/leave", me["token"], {"user": other["user"]})
    check("the owner removes the other member", (code, removed.get("ok")), (200, True))
    code, gone = call("/api/spaces/" + inv["s"] + "/likes", other["token"])
    check("and their access is gone", code, 403)
    page.click("#spaceback")
    page.wait_for_timeout(500)
    page.click('#spacelist [data-what="open"]')
    page.wait_for_timeout(2000)
    check("the owner still sees their own copy", len(page.query_selector_all("#spacelistitems .cap")), 1)
    body = page.inner_text("#spacelistitems")
    check("now alone in the space", "saved by 2" in body, False)
    # Their capture stays in the space (it was shared) but stops speaking for the group.
    check("and their copy is labelled as a former member's", "no longer in this space" in body, True)
    ctx.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
