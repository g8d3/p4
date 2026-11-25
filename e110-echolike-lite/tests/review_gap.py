"""What a hidden row may and may not do.

The owner's report after 1.23.1 was blunt: "there are jumps in the page, blank spaces
for some ads, and some posts seem to just disappear". The jumps were ours: X's phone
timeline positions rows absolutely (`li[data-index]` + inline `translateY`), and pulling
the later rows up by hand fought X's own re-measuring. The disappearing posts were a
recycled row keeping its mark.

So this pins the two guarantees that matter, and nothing clever:

  * the ad row is hidden, with its disclosure ("Ad from explee.com") and by itself;
  * **no other row is moved** — the offsets X wrote stay exactly as X wrote them, which
    is what keeps the page still;
  * a row that stops being an ad (X recycles it for a real post) is **visible again**;
  * switching the ads switch off leaves every row exactly where X put it.

A hidden row leaves its slot until X rebuilds the list. That is X's layout, said out
loud, instead of fighting it with geometry that made the page jump.

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

    # 1. "Ad from explee.com" is a disclosure, so the ad goes by itself.
    check("the ad is hidden", page.evaluate(HIDDEN, "ad1"), True)
    check("the ordinary posts stay", page.evaluate(HIDDEN, "post0"), False)
    check("and the one after it", page.evaluate(HIDDEN, "post2"), False)

    # 2. The page does not move: every offset is still the one X wrote.
    check("row 0 did not move", page.evaluate(TY % 0), 0.0)
    check("row 1 (the ad) did not move", page.evaluate(TY % 1), 200.0)
    check("row 2 did not move", page.evaluate(TY % 2), 400.0)

    # 3. X recycles the ad row for a real post: it must come back, not stay hidden.
    page.evaluate("""() => {
      const li = document.querySelector('li[data-index="1"]');
      li.removeAttribute('data-echolike-ad');
      const art = li.querySelector('article');
      art.querySelector('[dir="auto"][lang]').textContent = 'This is a real post now.';
      const label = art.querySelector('span:last-child');
      if (label && /explee/.test(label.textContent)) label.textContent = 'Somebody';
    }""")
    page.wait_for_timeout(300)
    check("a recycled row is visible again", page.evaluate(HIDDEN, "ad1"), False)

    # 4. Off leaves everything where X had it.
    page.evaluate("window.__setHideAds(false)")
    page.wait_for_timeout(200)
    check("row 0 at 0", page.evaluate(TY % 0), 0.0)
    check("row 1 at 200", page.evaluate(TY % 1), 200.0)
    check("row 2 at 400", page.evaluate(TY % 2), 400.0)
    check("nothing stays marked", page.evaluate("document.querySelectorAll('[data-echolike-ad]').length"), 0)
    check("no page errors", errors, [])

    browser.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
