"""The hole a hidden ad leaves is closed — and only the hole, and only once per layout.

The phone timeline positions rows absolutely (`li[data-index]` + an inline `translateY`),
so `display:none` removes the ad's box and keeps its slot: the rows below still count it.
X does not reclaim that slot on its own, so the hole is ours — and four releases of
trying to close it are four times the owner reported jumps:

  1. `transform: translateY(-h)` on the rows below — X rewrites `transform`, so it moved
     them twice or not at all and posts landed on top of each other (1.23.1);
  2. `translate` from a running total of measured gaps — the total swallowed X's spacing
     and the rows crept into each other (1.23.3);
  3. `translate` from an exact sum, plus a `style` observer — the observer fired on X's
     own writes on almost every scroll frame and each pass wrote layout again (1.23.5);
  4. no geometry at all — the hole was back, as the owner said (1.23.6).

1.23.7 closes it with a shift that cannot run away, and this file pins each of the four
rules that make that true:

  * the shift is `min(sum of hidden heights, the hole on screen)`, read from X's own
    numbers — so it can never push a row past the row above it;
  * nothing is derived from the `translate` we wrote, so recomputing is idempotent and X
    closing part of the hole shrinks the shift instead of doubling it;
  * X's own `transform` is never touched, and X's spacing between two posts survives;
  * the ads switch off removes every shift and leaves X's offsets as written.

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
  window.__ty = (i) => (document.querySelector('li[data-index="' + i + '"]').style.transform || '').trim();
  window.__tr = (i) => (document.querySelector('li[data-index="' + i + '"]').style.translate || '').trim();
  window.__gap = (a, b) => {
    const A = document.querySelector('li[data-index="' + a + '"]').getBoundingClientRect();
    const B = document.querySelector('li[data-index="' + b + '"]').getBoundingClientRect();
    return Math.round(B.top - A.bottom);
  };
  window.__nudge = () => {
    // what X does while you scroll: it appends a row (a childList change) — that is the
    // only trigger this code has, and re-settling must not move anything it already moved
    const li = document.createElement('li');
    li.setAttribute('data-index', '9');
    li.style.position = 'absolute';
    document.getElementById('list').appendChild(li);
    setTimeout(() => li.remove(), 50);
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

    # 1. The ad goes by itself: "Ad from explee.com" is a disclosure the word list knows.
    check("the ad is hidden", page.evaluate(HIDDEN, "ad1"), True)
    check("the ordinary posts stay", page.evaluate(HIDDEN, "post0"), False)
    check("and the one after it", page.evaluate(HIDDEN, "post2"), False)

    # 2. The hole is closed by exactly the ad's height, in `translate`; X's `transform`
    #    is untouched on every row, and X's own 30px spacing before row 2 survives.
    check("row 0 transform untouched", page.evaluate("window.__ty(0)"), "translateY(0px)")
    check("row 1 transform untouched", page.evaluate("window.__ty(1)"), "translateY(200px)")
    check("row 2 transform untouched", page.evaluate("window.__ty(2)"), "translateY(430px)")
    check("row 2 is pulled up by the ad's height", page.evaluate("window.__tr(2)"), "0px -200px")
    check("row 3 too (the whole tail moves)", page.evaluate("window.__tr(3)"), "0px -200px")
    check("row 4 too", page.evaluate("window.__tr(4)"), "0px -200px")
    check("row 0 (above the ad) is not moved", page.evaluate("window.__tr(0)"), "")
    check("the hole is closed and X's 30px gap survives", page.evaluate("window.__gap(0, 2)"), 30)

    # 2b. A second ad further down: the tail below it moves by both holes, not by the last
    #     one — an accumulation, which is the shape the two broken versions got wrong.
    check("the second ad is hidden", page.evaluate(HIDDEN, "ad5"), True)
    check("row 6 carries both holes", page.evaluate("window.__tr(6)"), "0px -400px")
    check("row 7 too", page.evaluate("window.__tr(7)"), "0px -400px")
    check("the post between the ads carries one", page.evaluate("window.__tr(4)"), "0px -200px")
    check("and the second hole is closed too", page.evaluate("window.__gap(4, 6)"), 30)

    # 3. Re-settling is idempotent: X appending a row (its own rhythm while you scroll)
    #    must not move anything again, and a scroll event moves nothing either.
    page.evaluate("window.__nudge()")
    page.wait_for_timeout(300)
    check("X appending a row moves nothing", page.evaluate("[window.__tr(2), window.__tr(3)]"), ["0px -200px", "0px -200px"])
    page.evaluate("window.dispatchEvent(new Event('scroll'))")
    page.wait_for_timeout(200)
    check("a scroll event moves nothing", page.evaluate("window.__tr(2)"), "0px -200px")
    check("no row overlaps the one above it", page.evaluate("window.__gap(0, 2) >= 0"), True)

    # 4. A post above the ad grows (a video loading) and X has not re-measured yet: the
    #    empty space is smaller now, so the shift shrinks with it. What must never happen
    #    is a shift bigger than the hole — the row would climb under the one above it.
    page.evaluate("""() => {
      document.querySelector('li[data-index="0"]').style.height = '300px';
      window.__nudge();
    }""")
    page.wait_for_timeout(300)
    check("a taller post above cannot push a row under it", page.evaluate("window.__gap(0, 2) >= 0"), True)
    check("and the tail still moves together", page.evaluate("window.__tr(2)") == page.evaluate("window.__tr(3)"), True)
    page.evaluate("""() => {
      document.querySelector('li[data-index="0"]').style.height = '200px';
      window.__nudge();
    }""")
    page.wait_for_timeout(300)
    check("and the shift comes back with the space", page.evaluate("window.__tr(2)"), "0px -200px")

    # 5. X closes the hole itself (it re-measures and rewrites the offset). The shift is
    #    derived from those numbers, so it shrinks to what is left — never doubles.
    page.evaluate("document.querySelector('li[data-index=\"2\"]').style.transform = 'translateY(230px)'")
    page.evaluate("window.__nudge()")
    page.wait_for_timeout(300)
    check("X's own offset is left as X wrote it", page.evaluate("window.__ty(2)"), "translateY(230px)")
    shift = page.evaluate("window.__tr(2)")
    check("the shift shrank with the hole", shift in ("", "0px -30px"), True)
    check("and nothing overlaps", page.evaluate("window.__gap(0, 2) >= 0"), True)
    page.evaluate("document.querySelector('li[data-index=\"2\"]').style.transform = 'translateY(430px)'")
    page.evaluate("window.__nudge()")
    page.wait_for_timeout(300)
    check("and it comes back when the hole does", page.evaluate("window.__tr(2)"), "0px -200px")

    # 6. X unmounts rows that scroll away — constantly. The record of what was closed is
    #    kept per list and per X index, not per mounted row, so losing the node must NOT
    #    move the rows below (that down-jump on unmount is what 1.23.7 did).
    check("an unmounted ad does not move the rows below", page.evaluate("""() => {
      const li = document.querySelector('li[data-index="1"]');
      window.__ad = li;
      const before = [window.__tr(2), window.__tr(3), window.__tr(6)];
      li.remove();
      window.__nudge();
      return [before, [window.__tr(2), window.__tr(3), window.__tr(6)]];
    }"""), [["0px -200px", "0px -200px", "0px -400px"], ["0px -200px", "0px -200px", "0px -400px"]])
    page.wait_for_timeout(300)
    page.evaluate("""() => { document.getElementById('list').appendChild(window.__ad); window.__nudge(); }""")
    page.wait_for_timeout(300)
    check("and it holds when the row comes back", page.evaluate("[window.__tr(2), window.__tr(6)]"), ["0px -200px", "0px -400px"])

    page.close()

    # 7. A row recycled into a real post: the post must be visible, and the rows below must
    #    sit right after it — never on top of it. (A real post in the slot means the slot is
    #    filled: the shift has to give way, and that is X's own re-layout, not a jump of ours.)
    page, errors2 = open_page(browser)
    page.evaluate("""() => {
      const li = document.querySelector('li[data-index="1"]');
      const art = li.querySelector('article');
      art.querySelector('[dir="auto"][lang]').textContent = 'This is a real post now.';
      const label = art.querySelector('span:last-child');
      if (label && /explee/.test(label.textContent)) label.textContent = 'Somebody';
      window.__nudge();
    }""")
    page.wait_for_timeout(400)
    check("a recycled row is visible again", page.evaluate(HIDDEN, "ad1"), False)
    check("the rows below sit after it, never on top of it", page.evaluate("window.__gap(1, 2) >= 0"), True)
    check("and the gap is X's own spacing, not an ad's height", page.evaluate("window.__gap(1, 2) <= 40"), True)

    # 8. Off: every shift goes, every offset stays exactly as X wrote it.
    page.evaluate("window.__setHideAds(false)")
    page.wait_for_timeout(200)
    check("nothing stays marked", page.evaluate("document.querySelectorAll('[data-echolike-ad]').length"), 0)
    check("nothing carries a translate of ours", page.evaluate("[window.__tr(0), window.__tr(2), window.__tr(3), window.__tr(4)]"), ["", "", "", ""])
    check("row 2 transform untouched", page.evaluate("window.__ty(2)"), "translateY(430px)")
    check("no page errors", errors + errors2, [])

    page.close()
    browser.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
