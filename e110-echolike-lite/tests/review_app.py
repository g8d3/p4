"""User seat: the extension is ONE page with two tabs.

There is no popup any more — the toolbar icon opens `app.html#inbox`, the Settings
tab holds everything else. This test loads the extension in a real Chrome, checks
the page exists without a popup, drives both tabs, and verifies the ads switch
still writes the flag the content script reads.
"""
import json
import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ids import extension_id  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"
MANIFEST = json.loads((EXT / "manifest.json").read_text())
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


check("the manifest has no popup", "default_popup" in MANIFEST.get("action", {}), False)
check("one page serves the whole extension", (EXT / "app.html").exists(), True)
check("no second screen left behind", (EXT / "popup.html").exists() or (EXT / "inbox.html").exists(), False)

prof = tempfile.mkdtemp(prefix="echolike-lite-app-")
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        prof, headless=False,
        args=[f"--disable-extensions-except={str(EXT)}", f"--load-extension={str(EXT)}", "--no-first-run"],
    )
    try:
        eid = extension_id()
        page = ctx.new_page()
        page.on("pageerror", lambda e: print("PAGEERROR", str(e)[:200]))
        page.goto(f"chrome-extension://{eid}/app.html")
        page.wait_for_timeout(700)

        # Opened without a hash: land on the inbox tab.
        check("defaults to the inbox tab", page.evaluate("location.hash"), "#inbox")
        shown = page.inner_text("#version")
        check("the page states its version", shown, "v" + MANIFEST["version"])
        check("inbox tab is selected", page.get_attribute("#tab-inbox", "aria-selected"), "true")
        check("settings panel hidden", page.is_visible("#url"), False)
        check("the one action is there", page.inner_text("#find"), "Find my inbox")
        status0 = page.inner_text("#status")
        check("empty state says what to press", "Find my inbox" in status0, True)
        check("and promises nothing to type", "nothing to type" in status0.lower(), True)

        # Seed two captures the way the content script would, then reopen.
        seeded = [
            {"uid": "u1", "kind": "like", "id": "111", "handle": "nasa",
             "url": "https://x.com/nasa/status/111", "text": "We are going back to the Moon.",
             "clicked_at": "2026-11-11T00:00:00Z"},
            {"uid": "u2", "kind": "bookmark", "id": "222", "handle": "sama",
             "url": "https://x.com/sama/status/222", "text": "scaling laws still hold <script>x</script>",
             "clicked_at": "2026-11-11T00:01:00Z"},
        ]
        page.evaluate("items => chrome.storage.local.set({items, outbox: items})", seeded)
        page.reload()
        page.wait_for_timeout(700)
        rows = page.query_selector_all("#list .cap")
        check("list rows", len(rows), 2)
        check("newest first", "sama" in (rows[0].inner_text() if rows else ""), True)
        check("XSS-safe", page.query_selector("#list script") is not None, False)
        check("waiting ones are called out", "waiting" in page.inner_text("#status"), True)

        # Tab switch: settings has the four cards and its own message line.
        page.click("#tab-settings")
        page.wait_for_timeout(300)
        check("hash follows the tab", page.evaluate("location.hash"), "#settings")
        check("settings visible", page.is_visible("#url"), True)
        cards = [page.inner_text(f"#panel-settings section:nth-of-type({i}) h2") for i in (1, 2, 3, 4)]
        check("four cards", len([c for c in cards if c]), 4)
        check("recovery code masked", page.get_attribute("#key", "type"), "password")
        page.click("#revealkey")
        check("reveal works", page.get_attribute("#key", "type"), "text")

        # The ads switch, now a settings row: it must write what the content script reads.
        check("ads hidden by default", page.is_checked("#ads"), True)
        page.uncheck("#ads")
        page.wait_for_timeout(250)
        check("uncheck writes storage", page.evaluate("chrome.storage.local.get({hide_ads:true}).then(s=>s.hide_ads)"), False)
        page.reload()
        page.wait_for_timeout(500)
        page.click("#tab-settings")
        page.wait_for_timeout(250)
        check("state survives a reload", page.is_checked("#ads"), False)
        page.check("#ads")
        page.wait_for_timeout(200)

        # Bad server: the settings card reports it, nothing is lost.
        page.fill("#url", "http://127.0.0.1:59999")
        page.fill("#token", "deadbeef")
        page.click("#save")
        page.wait_for_timeout(2500)
        check("bad connect reported", "unreachable" in page.inner_text("#inboxstatus").lower(), True)
        check("token field cleared", page.input_value("#token"), "")
        check("items kept", page.evaluate("chrome.storage.local.get({items:[]}).then(s=>s.items.length)"), 2)

        # Back to the inbox: the action hides itself once an inbox is configured.
        page.evaluate("chrome.storage.local.remove(['url','token'])")
        page.goto(f"chrome-extension://{eid}/app.html#inbox")
        page.wait_for_timeout(700)
        check("find button returns when disconnected", page.is_visible("#find"), True)
        check("and says what to do", "Find my inbox" in page.inner_text("#status"), True)
    finally:
        ctx.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
