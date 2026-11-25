"""The blank space: a virtualized row is hidden, its slot is closed too.

The owner's report was two sentences apart: "ads were hidden, but blank space remained"
and, later, "blank space is still there". The first rich ad report explained both — the
phone's timeline is a virtualized list where every row is `li[data-index]` positioned
absolutely with an inline `transform: translateY(<px>)`. `display:none` removes the box
and leaves the slot, so the rows after the ad keep their offsets and a hole stays exactly
where the ad was.

This pins the fix on that exact markup, and the disclosure that started it all
("Ad from explee.com", which the word list did not accept because it only knew "by"):

  * the ad row disappears;
  * the row after it moves up by the ad's height, so no hole is left;
  * the row before it does not move;
  * switching the ads switch off puts every row back where X had it.

    xvfb-run -a python3 tests/review_gap.py
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
CONTENT = (ROOT.parent / "extension" / "content.js").read_text()
FIXTURE = (ROOT / "fixture_virtual.html").resolve().as_uri()
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


TY = "(i) => { const el = document.querySelector('li[data-index=\"%d\"]'); const m = /translateY\\((-?[\\d.]+)px\\)/.exec(el.style.transform || ''); return m ? parseFloat(m[1]) : null }"
HIDDEN = "(i) => { const el = document.getElementById(i); return !el || el.getClientRects().length === 0 }"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)[:200]))
    page.goto(FIXTURE)
    page.add_script_tag(content=CONTENT)
    page.wait_for_timeout(250)

    # 1. "Ad from explee.com" is a disclosure now, so the ad goes by itself.
    check("the ad row's content is hidden", page.evaluate(HIDDEN, "ad1"), True)
    check("the ad row is marked", page.evaluate("document.querySelector('li[data-index=\"1\"]').getAttribute('data-echolike-ad')"), "1")
    check("the ordinary posts stay", page.evaluate(HIDDEN, "post0"), False)
    check("and the one after it", page.evaluate(HIDDEN, "post2"), False)

    # 2. The hole is closed: the row after the ad moved up by the ad's height (200px).
    check("the row after the ad moved up by its height", page.evaluate(TY % 2), 200.0)
    check("the row before it did not move", page.evaluate(TY % 0), 0.0)

    # 3. And it is reversible: switching the ads switch off restores X's own offsets.
    page.evaluate("window.__setHideAds(false)")
    page.wait_for_timeout(250)
    check("the ad is back", page.evaluate(HIDDEN, "ad1"), False)
    check("its row is back at 200", page.evaluate(TY % 1), 200.0)
    check("and the next row at 400", page.evaluate(TY % 2), 400.0)
    check("nothing stays marked", page.evaluate("document.querySelectorAll('[data-echolike-ad]').length"), 0)

    # 4. On again, and the collapse is recomputed, not doubled.
    page.evaluate("window.__setHideAds(true)")
    page.wait_for_timeout(250)
    check("hidden again", page.evaluate(HIDDEN, "ad1"), True)
    check("still one row-height up, not two", page.evaluate(TY % 2), 200.0)
    check("no page errors", errors, [])

    browser.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
