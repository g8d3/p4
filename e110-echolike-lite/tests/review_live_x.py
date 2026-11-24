"""The live X app, the real extension, one like: the only test that cannot go stale.

X rewrote x.com in 2026 ("x-web") and every fixture kept passing while capture
was dead, because fixtures encode yesterday's DOM. This one loads the unpacked
extension into a real Chrome, opens a public post on x.com (the logged-out pages
already run x-web), presses the real heart, and asks the extension what it stored.
It also pins the two diagnostics that make the next rewrite visible from the
field: `dom` (layout + control counts) and `capture` (kind + the same fingerprint).

    xvfb-run -a python3 tests/review_live_x.py
    ECHO_TEST_POST=https://x.com/<handle>/status/<id> xvfb-run -a python3 tests/review_live_x.py

Needs network. A local inbox on 8931/8911 is used if it accepts a claim; otherwise
the hosted inbox does. Either way it leaves one tenant/capture behind, like the
other live tests.
"""
import json
import os
import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
EXT = str((ROOT.parent / "extension").resolve())
MANIFEST = json.loads((ROOT.parent / "extension" / "manifest.json").read_text())
VERSION = MANIFEST["version"]
APPID = "jmfddigdennhnndgaecgppajnjabhlgm"  # the id of the key in .secrets/; see bin/publish.sh
POST = os.environ.get("ECHO_TEST_POST", "https://x.com/elonmusk/status/2125178828943184363")
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        tempfile.mkdtemp(prefix="echolike-live-"),
        headless=False,  # Chrome's old headless does not load extensions
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-sandbox"],
        viewport={"width": 1280, "height": 900},
    )

    page = ctx.new_page()
    page.goto(POST, wait_until="domcontentloaded")
    page.wait_for_selector("#echolike-lite-fab", state="attached", timeout=40000)
    check("the extension runs on the live page", True, True)
    check(
        "the page carries this version",
        page.evaluate(
            """() => document.getElementById('echolike-lite-fab').shadowRoot
                     .querySelector('.head small').textContent"""
        ),
        "v" + VERSION,
    )

    heart = page.locator('button:has(use[href="#icon-heart"])').first
    check("a heart button was found by icon, not testid", heart.count(), 1)
    heart.click()
    page.wait_for_timeout(2500)
    toast = page.evaluate("(() => { const t = document.getElementById('echolike-lite-toast'); return t && t.textContent })()")
    check("the like was acknowledged", bool(toast) and toast.startswith("EchoLike ✓"), True)

    ext = ctx.new_page()
    ext.goto(f"chrome-extension://{APPID}/app.html")
    ext.wait_for_timeout(800)
    st = ext.evaluate(
        """async () => {
             const s = await chrome.storage.local.get({ items: [], last: null, url: '', telemetry: [], telq: [] });
             return { items: s.items, last: s.last, url: s.url, actions: s.telemetry.map(e => e.action), queued: s.telq.length };
           }"""
    )
    check("one capture is in the browser", len(st["items"]), 1)
    if st["items"]:
        it = st["items"][0]
        check("it has a post id", bool(it.get("id")), True)
        check("it has the post text", bool(it.get("text")), True)
        check("it is a like or a bookmark", it.get("kind") in ("like", "unlike", "bookmark", "unbookmark"), True)
    check("it reached an inbox", bool(st["last"] and st["last"].get("ok")), True)
    check("the layout was reported", "dom" in st["actions"], True)
    check("the capture was reported", "capture" in st["actions"], True)
    check("the diagnostics queue drained", st["queued"], 0)

    ctx.close()

print()
if failures:
    print("FAILED: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
