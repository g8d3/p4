"""Install-and-done: a fresh browser, no configuration, one like.

This is the promise of the product in one test. The extension is loaded into a
clean profile, the user does nothing but like a post, and the capture has to
reach the hosted inbox on its own — no address typed, no token pasted, no button
pressed first.

    xvfb-run -a python3 tests/review_zero.py

Exit code 1 on any failure.
"""
import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ids import extension_id  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = str(ROOT / "extension")
HOST = "https://inbox-lite.echolike.app"
TEXT = "zero config capture " + str(int(__import__("time").time()))
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


prof = tempfile.mkdtemp(prefix="echolike-lite-zero-")
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        prof, headless=False,
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-first-run"],
    )
    try:
        page = ctx.new_page()
        page.on("pageerror", lambda e: print("PAGEERROR", str(e)[:200]))
        page.goto(f"chrome-extension://{extension_id()}/popup.html")
        page.wait_for_timeout(600)

        check("nothing configured", page.evaluate("chrome.storage.local.get({url:''}).then(s=>s.url)"), "")
        check("popup says there is nothing to set up", "Nothing to set up" in page.inner_text("#status"), True)
        check("no address field in sight", page.is_visible("#url"), False)

        reply = page.evaluate(
            """async (text) => await chrome.runtime.sendMessage({type:'capture', item:{
                 kind:'like', id:'901', handle:'nasa', url:'https://x.com/nasa/status/901',
                 text, clicked_at:new Date().toISOString()}})""",
            TEXT,
        )
        check("the like is acknowledged as sent", reply.get("sent"), True)
        check("it claimed the hosted inbox", page.evaluate("chrome.storage.local.get({url:''}).then(s=>s.url)"), HOST)
        check(
            "and kept the tenant token",
            len(page.evaluate("chrome.storage.local.get({token:''}).then(s=>s.token)")),
            32,
        )

        # Ask the hosted inbox, with the token the extension minted, whether it arrived.
        seen = page.evaluate(
            """async () => {
                 const s = await chrome.storage.local.get({url:'', token:''});
                 const r = await fetch(s.url + '/api/likes?limit=20', {headers:{authorization:'Bearer ' + s.token}});
                 return {status: r.status, body: await r.json()};
               }"""
        )
        check("hosted inbox answers with the extension token", seen["status"], 200)
        texts = [i.get("text") or "" for i in (seen["body"].get("items") or [])]
        check("the capture is stored there", TEXT in texts, True)
        check("tenant id reported", str(seen["body"].get("user", "")).startswith("u_"), True)

        page.reload()
        page.wait_for_timeout(700)
        check("popup now says connected", "Connected" in page.inner_text("#status"), True)
        check("open-inbox link points at the tenant", page.get_attribute("#open", "href").startswith(HOST + "/?t="), True)
        check("row rendered locally too", len(page.query_selector_all("#list div")), 1)
    finally:
        ctx.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
