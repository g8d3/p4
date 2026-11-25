"""The blank space after a hidden ad: measured, not fought.

Three rounds of this. The report that explained it: the phone's timeline is a
virtualized list where each row is `li[data-index]` positioned with an inline
`transform: translateY(<px>)`. Hiding a row leaves its hole, because the next row keeps
the pixel offset X wrote for it. 1.23.1 closed the hole by rewriting those offsets by
hand — X re-measures and rewrites them too, the two fought, and the page jumped with
posts landing on top of each other.

What 1.23.2 does, and what this pins:

  * the shift goes in the **`translate` property**, which composes with X's `transform`
    and which X never writes — so a re-render cannot fight it;
  * the shift is **measured on screen** (next row's offset minus the previous row's
    bottom): a hidden row contributes exactly its own height, and if X closes the hole
    by itself the measured hole is 0 and the shift disappears — it can never subtract
    twice;
  * X's own offsets are never touched, so nothing jumps;
  * a recycled row (X hands the element to a real post) is visible again;
  * switching the ads switch off clears every shift and every mark.

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
    const m = /translateY\\((-?[\\d.]+)px\\)/.exec(el.style.transform || '');
    return m ? parseFloat(m[1]) : null;
  };
  window.__shift = (i) => {
    const el = document.querySelector('li[data-index="' + i + '"]');
    return el.style.translate || '';
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

    # 1. "Ad from explee.com" is a disclosure, so the ad goes by itself.
    check("the ad is hidden", page.evaluate(HIDDEN, "ad1"), True)
    check("the ordinary posts stay", page.evaluate(HIDDEN, "post0"), False)
    check("and the one after it", page.evaluate(HIDDEN, "post2"), False)

    # 2. X's own offsets are untouched — that is what keeps the page still.
    check("row 0 did not move", page.evaluate("window.__ty(0)"), 0.0)
    check("row 1 (the ad) did not move", page.evaluate("window.__ty(1)"), 200.0)
    check("row 2 did not move", page.evaluate("window.__ty(2)"), 400.0)

    # 3. The hole is closed by the measured shift, in a property X does not write.
    check("row 2 is pulled up by the hidden row's height", page.evaluate("window.__shift(2)"), "0px -200px")
    check("the rows above it are not", page.evaluate("window.__shift(0)"), "")
    box = page.evaluate("""() => {
      const a = document.querySelector('li[data-index="0"]').getBoundingClientRect();
      const c = document.querySelector('li[data-index="2"]').getBoundingClientRect();
      return Math.round(c.top - a.bottom);   // hole the hidden row used to leave
    }""")
    check("no blank space is left between the rows", box, 0)

    # 4. Off leaves everything where X had it, shift and marks included.
    page.evaluate("window.__setHideAds(false)")
    page.wait_for_timeout(200)
    check("the ad is back", page.evaluate(HIDDEN, "ad1"), False)
    check("no shift survives the switch", page.evaluate("document.querySelectorAll('[data-ech-shift]').length"), 0)
    check("row 2 is back at X's 400", page.evaluate("window.__ty(2)"), 400.0)
    check("nothing stays marked", page.evaluate("document.querySelectorAll('[data-echolike-ad]').length"), 0)

    # 5. On again, and the shift is recomputed, not doubled.
    page.evaluate("window.__setHideAds(true)")
    page.wait_for_timeout(250)
    check("hidden again", page.evaluate(HIDDEN, "ad1"), True)
    check("still one row-height up, not two", page.evaluate("window.__shift(2)"), "0px -200px")

    # 6. A virtualized row is recycled for a real post: it must come back.
    page.evaluate("""() => {
      const li = document.querySelector('li[data-index="1"]');
      const art = li.querySelector('article');
      art.querySelector('[dir="auto"][lang]').textContent = 'This is a real post now.';
      const label = art.querySelector('span:last-child');
      if (label && /explee/.test(label.textContent)) label.textContent = 'Somebody';
    }""")
    page.wait_for_timeout(300)
    check("a recycled row is visible again", page.evaluate(HIDDEN, "ad1"), False)
    check("no page errors", errors, [])
    page.close()

    # 7. If X closes the hole by itself, the measured shift must vanish — or the rows
    #    would be pulled up twice. Here X rewrites row 2 to 200 (its own re-measure).
    page, errors = open_page(browser)
    page.evaluate("""() => {
      const row = document.querySelector('li[data-index="2"]');
      row.style.transform = 'translateY(200px)';   // X closed the slot by itself
      window.dispatchEvent(new Event('scroll'));
    }""")
    page.wait_for_timeout(300)
    check("no shift once X closed the hole itself", page.evaluate("window.__shift(2)"), "")
    check("and its offset is still X's", page.evaluate("window.__ty(2)"), 200.0)
    check("no page errors after X re-measures", errors, [])
    page.close()

    browser.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
