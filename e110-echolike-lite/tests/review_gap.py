"""Ads are hidden by one attribute and one CSS rule — and no layout is written.

Four rounds of "blank space", and the lesson each one paid for:

  1. `display:none` alone leaves the slot of a virtualized row (rows are
     `li[data-index]` with an inline `translateY`), so the owner saw blank space;
  2. moving those rows by rewriting `transform` made the page **jump**, because X
     rewrites the same property when it re-measures;
  3. moving them in the `translate` property instead survived the fight, but X **reads
     layout back** — and the page started drawing posts twice;
  4. so: no geometry at all. Hide the row, leave X's offsets untouched, re-check rows that
     are recycled so a real post never inherits a mark.

What this pins:

  * the ad goes (its disclosure is "Ad from explee.com", a form the word list now knows);
  * **no row's inline `transform` is modified** and no `translate` is written;
  * the hole stays where X leaves it — accepted out loud, because closing it is what
    broke the page twice;
  * a recycled row is visible again;
  * switching the ads switch off leaves every offset exactly as X wrote it.

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


SETUP = """() => {
  window.__ty = (i) => {
    const el = document.querySelector('li[data-index="' + i + '"]');
    return (el.style.transform || '').trim();
  };
  window.__tr = (i) => {
    const el = document.querySelector('li[data-index="' + i + '"]');
    return (el.style.translate || '').trim();
  };
}"""
HIDDEN = "(i) => { const el = document.getElementById(i); return !el || el.getClientRects().length === 0 }"


def open_page(browser):
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)[:200]))
    page.goto(FIXTURE)
    page.add_script_tag(content=CONTENT)
    page.evaluate(SETUP)
    page.wait_for_timeout(250)
    return page, errors


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    page, errors = open_page(browser)

    # 1. The ad goes by itself: "Ad from explee.com" is a disclosure now.
    check("the ad is hidden", page.evaluate(HIDDEN, "ad1"), True)
    check("the ordinary posts stay", page.evaluate(HIDDEN, "post0"), False)
    check("and the one after it", page.evaluate(HIDDEN, "post2"), False)

    # 2. Only `translate` is written — never X's `transform` — and by exactly the hidden
    #    row's height. X's own 30px spacing before row 2 is not touched.
    check("row 0 transform untouched", page.evaluate("window.__ty(0)"), "translateY(0px)")
    check("row 1 transform untouched", page.evaluate("window.__ty(1)"), "translateY(200px)")
    check("row 2 transform untouched", page.evaluate("window.__ty(2)"), "translateY(430px)")
    check("row 2 is pulled up by the ad's height, and by that alone", page.evaluate("window.__tr(2)"), "0px -200px")
    check("row 0 is not moved", page.evaluate("window.__tr(0)"), "")
    gapv = page.evaluate("""() => {
      const a = document.querySelector('li[data-index="0"]').getBoundingClientRect();
      const c = document.querySelector('li[data-index="2"]').getBoundingClientRect();
      return Math.round(c.top - a.bottom);   // the ad's slot, and X's own gap
    }""")
    check("the hole is closed and X's 30px gap survives", gapv, 30)

    # 3. A scroll changes nothing (there is no scroll listener any more).
    page.evaluate("window.dispatchEvent(new Event('scroll'))")
    page.wait_for_timeout(200)
    check("a scroll event moves nothing", page.evaluate("window.__tr(2)"), "0px -200px")

    # 3b. X re-measures and closes the slot by itself: the shift must go, not double.
    page.evaluate("document.querySelector('li[data-index=\"2\"]').style.transform = 'translateY(200px)'")
    page.wait_for_timeout(300)
    check("no double shift once X closed the hole", page.evaluate("window.__tr(2)"), "")
    page.evaluate("document.querySelector('li[data-index=\"2\"]').style.transform = 'translateY(430px)'")
    page.wait_for_timeout(300)
    check("and the shift comes back when the hole does", page.evaluate("window.__tr(2)"), "0px -200px")

    # 4. A recycled row (X hands the element to a real post) must come back.
    page.evaluate("""() => {
      const li = document.querySelector('li[data-index="1"]');
      const art = li.querySelector('article');
      art.querySelector('[dir="auto"][lang]').textContent = 'This is a real post now.';
      const label = art.querySelector('span:last-child');
      if (label && /explee/.test(label.textContent)) label.textContent = 'Somebody';
    }""")
    page.wait_for_timeout(300)
    check("a recycled row is visible again", page.evaluate(HIDDEN, "ad1"), False)

    # 5. Off leaves everything as X wrote it, marks included.
    page.evaluate("window.__setHideAds(false)")
    page.wait_for_timeout(200)
    check("nothing stays marked", page.evaluate("document.querySelectorAll('[data-echolike-ad]').length"), 0)
    check("row 0 transform untouched", page.evaluate("window.__ty(0)"), "translateY(0px)")
    check("row 2 transform untouched", page.evaluate("window.__ty(2)"), "translateY(430px)")
    check("nothing is moved by us any more", page.evaluate("[window.__tr(0), window.__tr(1), window.__tr(2)]"), ["", "", ""])
    check("no page errors", errors, [])

    page.close()
    browser.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
