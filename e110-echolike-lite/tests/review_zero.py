"""Install-and-done: a fresh browser, no configuration, one like.

This is the promise of the product in one test. The extension is loaded into a
clean profile, the user does nothing but like a post, and the capture has to
reach the hosted inbox on its own — no address typed, no token pasted, no button
pressed first.

    xvfb-run -a python3 tests/review_zero.py

Exit code 1 on any failure.
"""
import json
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
        page.goto(f"chrome-extension://{extension_id()}/app.html#inbox")
        page.wait_for_timeout(600)

        check("nothing configured", page.evaluate("chrome.storage.local.get({url:''}).then(s=>s.url)"), "")
        status0 = page.inner_text("#status")
        check("the page says it is not connected", "Not connected" in status0, True)
        check("and tells the user what to press", "Find my inbox" in status0, True)
        check("no settings fields on the inbox tab", page.is_visible("#url"), False)

        reply = page.evaluate(
            """async (text) => await chrome.runtime.sendMessage({type:'capture', item:{
                 kind:'like', id:'901', handle:'nasa', url:'https://x.com/nasa/status/901',
                 text, clicked_at:new Date().toISOString()}})""",
            TEXT,
        )
        if not page.evaluate("chrome.storage.local.get({url:''}).then(s=>s.url)"):
            print("  note: no inbox was claimed (rate-limited or offline) — claim is capped per IP per hour")
            print("FAILURES:", failures + ["claim"])
            sys.exit(1)
        check("the like is acknowledged as sent", reply.get("sent"), True)
        check("it claimed the hosted inbox", page.evaluate("chrome.storage.local.get({url:''}).then(s=>s.url)"), HOST)
        check(
            "and kept the tenant token",
            len(page.evaluate("chrome.storage.local.get({token:''}).then(s=>s.token)")),
            32,
        )

        check("a key was generated here", len(page.evaluate("chrome.storage.local.get({key:''}).then(s=>s.key)")), 43)

        # Ask the hosted inbox what it holds. It must hold a blob, not the words.
        seen = page.evaluate(
            """async () => {
                 const s = await chrome.storage.local.get({url:'', token:''});
                 const r = await fetch(s.url + '/api/likes?limit=20', {headers:{authorization:'Bearer ' + s.token}});
                 return {status: r.status, raw: await r.text()};
               }"""
        )
        check("hosted inbox answers with the extension token", seen["status"], 200)
        check("the server never sees the words", TEXT in seen["raw"] or "nasa" in seen["raw"], False)
        check("it stores ciphertext", '"ct"' in seen["raw"], True)
        body = json.loads(seen["raw"])
        check("tenant id reported", str(body.get("user", "")).startswith("u_"), True)

        # The extension's own inbox page decrypts that blob with the local key.
        inbox = ctx.new_page()
        inbox.on("pageerror", lambda e: print("PAGEERROR", str(e)[:200]))
        inbox.goto(f"chrome-extension://{extension_id()}/app.html#inbox")
        inbox.wait_for_timeout(2500)
        text = inbox.inner_text("#list")
        check("the inbox tab decrypts it", TEXT in text, True)
        check("and shows the post author", "@nasa" in text, True)
        check("quota line rendered", "this month" in inbox.inner_text("#status"), True)
        check("export offered", inbox.is_visible("#export"), True)
        inbox.close()

        page.reload()
        page.wait_for_timeout(700)
        check("inbox tab shows the inbox it chose", "inbox-lite.echolike.app" in page.inner_text("#status"), True)
        href = page.evaluate("document.getElementById('open').href")
        check("open on echolike.app", href.startswith(HOST + "/#t="), True)
        check("the key rides in the fragment, not the query", "&k=" in href and href.split("#")[0].count("k=") == 0, True)
        check("the link names the site", "echolike.app" in page.inner_text("#webinbox"), True)

        # Follow that link for real: a plain web page, no extension, decrypts it.
        web = ctx.new_page()
        web.goto(href)
        web.wait_for_timeout(3000)
        webtext = web.inner_text("#list")
        check("the web inbox shows the capture", TEXT in webtext, True)
        check("and says it is in the inbox", "in the" in web.inner_text("#status") or "capture" in web.inner_text("#status"), True)
        web.close()
        opts = ctx.new_page()
        opts.goto(f"chrome-extension://{extension_id()}/app.html#settings")
        opts.wait_for_timeout(700)
        check("recovery code shown in settings", len(opts.input_value("#key")), 43)
        check("recovery code is masked until revealed", opts.get_attribute("#key", "type"), "password")
        opts.click("#revealkey")
        check("reveal works", opts.get_attribute("#key", "type"), "text")
        opts.close()
        check("row rendered locally too", len(page.query_selector_all("#list .cap")), 1)
    finally:
        ctx.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
