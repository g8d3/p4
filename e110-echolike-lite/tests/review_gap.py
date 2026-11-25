"""Ads are hidden by one attribute and one CSS rule — and the page is never moved.

Five releases of "the page jumps", and what each one taught:

  1. `display:none` alone leaves the slot of a virtualized row (rows are
     `li[data-index]` with an inline `translateY`), so the owner saw blank space;
  2. moving those rows by rewriting `transform` made the page jump, because X
     rewrites the same property when it re-measures;
  3. moving them in the `translate` property instead survived that fight, but X
     **reads layout back** — the page started drifting and drawing posts twice;
  4. 1.23.5 added a `style` observer to keep that bookkeeping in sync with X, which
     turned into a loop: X writes `style` on its rows on almost every scroll frame,
     we wrote layout back on every one of those, and the page jumped continuously;
  5. and every mutation re-judged every post, so an X repaint that dropped the
     disclosure for one frame **un-hid the ad**, the row grew back, and it was hidden
     again — a jump several times a second.

So 1.23.6 writes no geometry at all and a mark, once recognised, is sticky: it is
dropped only when the cell holds a DIFFERENT post.

What this pins:

  * the ad goes (its disclosure is "Ad from explee.com", a form the word list knows);
  * **no inline `transform` is modified, no `translate` is written, and no box of
    ours changes any row's size or position** — checked before/after, and again after
    X-style mutations that used to trigger the bookkeeping;
  * a repaint of the ad's own header does not bring it back (the anti-flicker rule);
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
  // Everything a "jump" can be made of, on every row we did not hide, and every style
  // attribute in the document — our writes would have to show up in one of them.
  window.__geom = () => [...document.querySelectorAll('li[data-index]')].map((el) => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return [el.dataset.index, Math.round(r.top), Math.round(r.height),
            (el.getAttribute('style') || '').trim(),
            cs.transform, cs.translate, cs.marginTop, cs.paddingTop].join('|');
  }).join('\\n');
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

    # 2. Nothing of ours moves anything: X's three offsets are exactly as written, no
    #    `translate` exists, and no row's box or style changed.
    check("row 0 transform untouched", page.evaluate("window.__ty(0)"), "translateY(0px)")
    check("row 1 transform untouched", page.evaluate("window.__ty(1)"), "translateY(200px)")
    check("row 2 transform untouched", page.evaluate("window.__ty(2)"), "translateY(430px)")
    check("nothing carries a translate of ours", page.evaluate("[window.__tr(0), window.__tr(1), window.__tr(2)]"), ["", "", ""])
    geometric_before = page.evaluate("window.__geom()")

    # 3. X does what it does while scrolling (rewrites the rows' own transforms, swaps
    #    text inside posts). The list must come out the way X left it, every time.
    page.evaluate("""() => {
      const rows = document.querySelectorAll('li[data-index]');
      for (const r of rows) r.style.transform = r.style.transform;  // X re-measures
      const p = document.querySelector('#post0 [dir="auto"][lang]');
      p.textContent = 'An ordinary post, edited.';
    }""")
    page.wait_for_timeout(200)
    check("X's re-measure changes nothing of ours", page.evaluate("window.__geom()"), geometric_before)

    # 4. A repaint of the ad's own header (the label momentarily gone) must not bring the
    #    ad back: that flicker was a jump, several times a second, while scrolling.
    page.evaluate("""() => {
      const label = document.querySelector('#ad1 span:last-child');
      label.textContent = '';                       // the disclosure disappears for a frame
    }""")
    page.wait_for_timeout(200)
    check("the ad stays hidden while X repaints it", page.evaluate(HIDDEN, "ad1"), True)
    page.evaluate("""() => {
      document.querySelector('#ad1 span:last-child').textContent = 'Ad from explee.com';
    }""")
    page.wait_for_timeout(200)
    check("and after the label comes back", page.evaluate(HIDDEN, "ad1"), True)
    check("no geometry written during the repaint", page.evaluate("window.__geom()"), geometric_before)

    # 5. A scroll event changes nothing (there is no scroll listener at all).
    page.evaluate("window.dispatchEvent(new Event('scroll'))")
    page.wait_for_timeout(200)
    check("a scroll event moves nothing", page.evaluate("window.__geom()"), geometric_before)

    # 6. A recycled row (X hands the element to a real post) must come back: the mark
    #    belongs to a post, and this is a different one.
    page.evaluate("""() => {
      const li = document.querySelector('li[data-index="1"]');
      const art = li.querySelector('article');
      art.querySelector('[dir="auto"][lang]').textContent = 'This is a real post now.';
      const label = art.querySelector('span:last-child');
      if (label && /explee/.test(label.textContent)) label.textContent = 'Somebody';
    }""")
    page.wait_for_timeout(300)
    check("a recycled row is visible again", page.evaluate(HIDDEN, "ad1"), False)

    # 7. Off leaves everything as X wrote it, marks included.
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
