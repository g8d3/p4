"""Two strangers who saved the same posts, finding each other with no codes at all.

That is the whole point of this feature. The owner's question was: two users cannot find
each other, and every path so far made one of them manage a code. So:

  * each device publishes an ECDH P-256 public key;
  * an opted-in user publishes a BLIND index — sha256(kind|post id), no text, no handle;
  * the server ranks overlaps and hands back pseudonyms + public keys;
  * an invitation is ADDRESSED to a user, with the space key wrapped to their device key.

This test drives two real extension installs. Nothing types a code: A looks for people,
presses Invite, and B finds the invitation waiting, accepts, and reads A's shared posts.

    python3 tests/review_discovery.py

Exit code 1 on any failure.
"""
import datetime
import json
import pathlib
import sys
import tempfile
import urllib.request

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ids import extension_id  # noqa: E402
from tenant import tenant as get_tenant  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"
BASE = "https://inbox-lite.echolike.app"
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


def call(path, token=None, body=None, method=None):
    h = {"content-type": "application/json", "user-agent": "Mozilla/5.0 Chrome/140.0"}
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


def cap(uid, post, handle):
    return {
        "uid": uid,
        "kind": "like",
        "id": post,
        "handle": handle,
        "author_name": handle,
        "url": "https://x.com/%s/status/%s" % (handle, post),
        "text": "shared interest " + post,
        "clicked_at": "2026-11-12T10:00:00Z",
        "captured_at": "2026-11-12T10:00:01Z",
        "counts": {"likes": 3},
    }


def boot(ctx, tenant, items):
    page = ctx.new_page()
    page.on("pageerror", lambda e: failures.append("pageerror: " + str(e)[:140]))
    page.goto(f"chrome-extension://{extension_id()}/app.html#spaces")
    page.wait_for_timeout(700)
    page.evaluate(
        "({url, token, items}) => chrome.storage.local.set({url, token, items, outbox: []})",
        {"url": BASE, "token": tenant["token"], "items": items},
    )
    page.reload()
    page.wait_for_timeout(1500)
    return page


with sync_playwright() as p:
    A = p.chromium.launch_persistent_context(tempfile.mkdtemp(prefix="echolike-disc-a-"), headless=False,
                                             args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-first-run"])
    B = p.chromium.launch_persistent_context(tempfile.mkdtemp(prefix="echolike-disc-b-"), headless=False,
                                             args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-first-run"])
    a_tenant = get_tenant("disc-a")
    b_tenant = get_tenant("disc-b")

    # Unique post ids per run: identical synthetic posts from an earlier run would
    # outrank the real match and the test would invite a ghost.
    run = str(int(datetime.datetime.now().timestamp()))
    shared, otherA, otherB = "1" + run, "2" + run, "9" + run
    page_a = boot(A, a_tenant, [cap("a1", shared, "nasa"), cap("a2", otherA, "sama")])
    page_b = boot(B, b_tenant, [cap("b1", shared, "nasa"), cap("b2", otherB, "x")])

    # A creates a space and shares its captures into it, before inviting anybody.
    page_a.fill("#spacename", "afines")
    page_a.click("#spacecreate")
    page_a.wait_for_timeout(1500)
    page_a.click('#spacelist [data-what="share"]')
    page_a.wait_for_timeout(2500)

    # Both opt in. Nothing but hashes travels.
    for page in (page_a, page_b):
        page.check("#discovery-on")
        page.wait_for_timeout(2500)
    check("A published its blind index", "posts in your blind index" in page_a.inner_text("#discovery-state"), True)
    code, st = call("/api/discovery", a_tenant["token"])
    check("the server counts hashes, not posts", (st.get("enabled"), st.get("hashes")), (True, 2))

    # A looks for people with the same interests: B shows up, with the shared post count.
    page_a.click("#discovery-find")
    page_a.wait_for_timeout(2500)
    listing = page_a.inner_text("#matchlist")
    check("A finds B by shared interests", b_tenant["user"].replace("u_", "") in listing, True)
    check("and the overlap is a number", "1 post in common" in listing, True)
    check("A never had to know B's code", page_a.is_visible('[data-invite-user]'), True)

    # A invites B straight from the match: no code, no copy-paste.
    page_a.click("[data-invite-user]")
    page_a.wait_for_timeout(2500)
    check("the invitation was sent", "invited" in page_a.inner_text('[data-inv-msg]'), True)
    code, pend = call("/api/invites", b_tenant["token"])
    check("it is addressed to B", (code, len(pend.get("invites", []))), (200, 1))
    check("and it carries a boxed key, not the key", bool(pend["invites"][0]["wrapped"]), True)

    # B opens Spaces: the invitation is waiting, accepts, and can read A's posts.
    page_b.reload()
    page_b.wait_for_timeout(2000)
    inbox = page_b.inner_text("#invitelist")
    check("B sees the invitation without a code", "afines" in inbox, True)
    page_b.click("[data-accept]")
    page_b.wait_for_timeout(3000)
    check("B is in the space", "afines" in page_b.inner_text("#spacelist"), True)
    # B shares its own copy too: that is what makes the card count two people.
    page_b.click('#spacelist [data-what="share"]')
    page_b.wait_for_timeout(2500)
    page_b.click('#spacelist [data-what="open"]')
    page_b.wait_for_timeout(2500)
    body = page_b.inner_text("#spacelistitems")
    check("B reads A's shared posts", "shared interest " + shared in body and "shared interest " + otherA in body, True)
    check("two people counted on the card", "saved by 2 people here" in body, True)

    # Opting out deletes the index and the matches disappear with it.
    page_b.uncheck("#discovery-on")
    page_b.wait_for_timeout(2000)
    code, st = call("/api/discovery", b_tenant["token"])
    check("opting out removes what was published", (st.get("enabled"), st.get("hashes")), (False, 0))
    page_a.click("#discovery-find")
    page_a.wait_for_timeout(2500)
    check("and A can no longer match B", "1 post in common" in page_a.inner_text("#matchlist"), False)

    A.close()
    B.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
