"""The circle on x.com: the extension, and its version, on the page itself.

What the owner asked for, and what this pins down:
  * the version is visible on x.com (panel header, hover title, footer);
  * a movable circle (drag), whose position survives a reload, clamped to the screen;
  * pressing it opens the extension's functions: inbox, settings, export likes,
    export bookmarks, export everything — plus the count of what is still queued;
  * exporting works with no inbox, no server and no account: the mirror in this
    browser is the file;
  * "Hide this button" turns it off for real (a storage flag the Settings tab flips back).

Driven against the X-shaped fixture in a real browser, so no X account is needed.

    xvfb-run -a python3 tests/review_fab.py

Exit code 1 on any failure.
"""
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
CONTENT = (ROOT.parent / "extension" / "content.js").read_text()
MANIFEST = json.loads((ROOT.parent / "extension" / "manifest.json").read_text())
VERSION = MANIFEST["version"]
fixture = ROOT / "fixture.html"
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


MIRROR = [
    {"uid": "m1", "kind": "like", "id": "111", "handle": "nasa", "text": "a", "clicked_at": "2026-11-11T10:00:00Z"},
    {"uid": "m2", "kind": "like", "id": "222", "handle": "sama", "text": "b", "clicked_at": "2026-11-11T11:00:00Z"},
    {"uid": "m3", "kind": "bookmark", "id": "333", "handle": "x", "text": "c", "clicked_at": "2026-11-11T12:00:00Z"},
]


def fab(page, js):
    """Evaluate inside the shadow root: page.evaluate cannot see into it by selector."""
    return page.evaluate(
        """(js) => {
          const host = document.getElementById('echolike-lite-fab');
          if (!host || !host.shadowRoot) return null;
          // 'document' inside the expression is the shadow root: selectors stay
          // readable, and nothing leaks to the page's own DOM.
          return new Function('r', 'const document = r; return (' + js + ')')(host.shadowRoot);
        }""",
        js,
    )


def press(page):
    """A real pointer click: the panel opens on pointerup, not on a synthetic click."""
    box = fab(page, "(() => { const r = document.querySelector('.dot').getBoundingClientRect(); return [r.left, r.top] })()")
    page.mouse.click(box[0] + 21, box[1] + 21)
    page.wait_for_timeout(150)


def boot(page, store=None):
    page.goto(fixture.as_uri())
    page.evaluate("v => { window.__VERSION = v }", VERSION)
    page.evaluate("m => { window.__mirror = m }", MIRROR)
    page.evaluate("m => window.__setStore({items: m})", MIRROR)
    if store:
        page.evaluate("s => window.__setStore(s)", store)
    page.add_script_tag(content=CONTENT)
    page.wait_for_timeout(250)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1100, "height": 800})
    page.on("pageerror", lambda e: failures.append("pageerror: " + str(e)[:120]))
    boot(page, {"outbox": [{"uid": "q1"}, {"uid": "q2"}]})

    # 1. It exists, it is a shadow root (X's CSS cannot reach it), and it says the version.
    check("the launcher is mounted", page.evaluate("!!document.getElementById('echolike-lite-fab')"), True)
    check("it lives in a shadow root", page.evaluate("!!document.getElementById('echolike-lite-fab').shadowRoot"), True)
    check("its title carries the version", fab(page, "document.querySelector('.dot').title").find("v" + VERSION) >= 0, True)
    check("it sits on the page, not in a corner of it", fab(page, "getComputedStyle(document.querySelector('.dot')).position"), "fixed")
    check("the panel starts closed", fab(page, "document.querySelector('.panel').classList.contains('on')"), False)
    check("the pending count is on the circle", fab(page, "document.querySelector('.dot').getAttribute('data-pending')"), "1")
    check("and it says how many", fab(page, "document.querySelector('.dot b').textContent"), "2")

    # 2. Press: the panel shows what the extension can do, version included.
    press(page)
    check("press opens the panel", fab(page, "document.querySelector('.panel').classList.contains('on')"), True)
    head = fab(page, "document.querySelector('.head').textContent")
    check("the panel states the version", ("v" + VERSION) in head, True)
    check("the panel carries its own code", fab(page, "document.querySelector('.head .code').textContent"), "X1")
    labels = fab(page, "[...document.querySelectorAll('.panel button')].map(b => b.textContent)")
    check("it offers the inbox", any("My inbox" in x for x in labels), True)
    check("it offers the settings", any("Settings" in x for x in labels), True)
    check("it offers the three exports, with counts", labels[2:], ["Export likes (2)", "Export bookmarks (1)", "Export everything (3)"])

    # 3. Open the inbox / settings: the page asks the extension for a tab.
    fab(page, "[...document.querySelectorAll('.panel button')].find(b => b.dataset.page === 'settings').click(), 1")
    page.wait_for_timeout(150)
    check("settings is asked for", page.evaluate("window.__opened"), ["settings"])

    # 4. Export: a real file, from the mirror, with no server involved.
    with page.expect_download() as dl:
        fab(page, "[...document.querySelectorAll('.panel button')].find(b => b.dataset.pick === 'likes').click(), 1")
    d = dl.value
    path = d.path()
    data = json.loads(pathlib.Path(path).read_text())
    check("the file is named for what it holds", d.suggested_filename, "echolike-likes-%s.json" % __import__("datetime").date.today().isoformat())
    check("it holds only the likes", [i["uid"] for i in data], ["m1", "m2"])
    check("the panel confirms it", fab(page, "document.querySelector('.status').textContent"), "downloaded 2 likes")

    # 5. Drag: the button moves, the position is saved, and it survives a reload.
    page.keyboard.press("Escape")
    page.wait_for_timeout(100)
    check("Escape closes the panel", fab(page, "document.querySelector('.panel').classList.contains('on')"), False)
    before = fab(page, "[document.querySelector('.dot').style.left, document.querySelector('.dot').style.top]")
    box = fab(page, "(() => { const r = document.querySelector('.dot').getBoundingClientRect(); return [r.left, r.top] })()")
    page.mouse.move(box[0] + 20, box[1] + 20)
    page.mouse.down()
    page.mouse.move(box[0] - 300, box[1] - 200, steps=12)
    page.mouse.up()
    page.wait_for_timeout(200)
    after = fab(page, "[document.querySelector('.dot').style.left, document.querySelector('.dot').style.top]")
    check("dragging moved it", after != before, True)
    check("the panel did not open by accident", fab(page, "document.querySelector('.panel').classList.contains('on')"), False)
    saved = page.evaluate("window.__writes.filter(w => 'fab_x' in w).slice(-1)[0]")
    check("the position was saved", (round(saved["fab_x"]), round(saved["fab_y"])), (round(float(after[0][:-2])), round(float(after[1][:-2]))))

    boot(page, {"outbox": [], "fab_x": saved["fab_x"], "fab_y": saved["fab_y"]})
    restored = fab(page, "[document.querySelector('.dot').style.left, document.querySelector('.dot').style.top]")
    check("a reload puts it back where it was", restored, after)
    check("no pending captures, no badge", fab(page, "document.querySelector('.dot').getAttribute('data-pending')"), None)

    # 6. It never leaves the screen: a position beyond the edge is clamped.
    boot(page, {"fab_x": 99999, "fab_y": 99999})
    spot = fab(page, "[parseFloat(document.querySelector('.dot').style.left), parseFloat(document.querySelector('.dot').style.top)]")
    check("a stored position is clamped to the viewport", spot[0] <= 1100 and spot[1] <= 800, True)

    # 7. Hide: for real, and restorable from Settings.
    press(page)
    fab(page, "[...document.querySelectorAll('.panel [data-act]')].find(b => b.dataset.act === 'hide').click(), 1")
    page.wait_for_timeout(150)
    check("hide removes it", page.evaluate("!!document.getElementById('echolike-lite-fab')"), False)
    check("and the flag is off", page.evaluate("window.__writes.slice(-1)[0].fab_on"), False)

    boot(page, {"fab_on": False})
    check("off means off on a fresh page", page.evaluate("!!document.getElementById('echolike-lite-fab')"), False)
    page.evaluate("window.__emitChange({fab_on: {newValue: true}})")
    page.wait_for_timeout(150)
    check("Settings can turn it back on without a reload", page.evaluate("!!document.getElementById('echolike-lite-fab')"), True)

    # 8. A like still captures with the launcher present (it must not steal the click).
    page.click('article:nth-of-type(1) [data-testid="like"]')
    page.wait_for_timeout(150)
    check("liking still captures", len(page.evaluate("window.__sent")), 1)

    browser.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
