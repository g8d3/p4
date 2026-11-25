"""Marking an ad on the page: the owner's own eyes as the detector.

The field report was `articles=8 marked=0 | no disclosure label found` — an ad whose
word this product has never seen, so no rule could have caught it and a guess would
have been another release. This is the way out of that loop: on X, press the circle →
**Mark an ad…**, tap the ad. It disappears on the spot, its shape is reported, and the
word that is unique to it is kept as a candidate. A second mark of the same kind
teaches the word, and from then on ads that use it hide by themselves — including
after a reload.

    xvfb-run -a python3 tests/review_mark.py
"""
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
CONTENT = (ROOT.parent / "extension" / "content.js").read_text()
FIXTURE = (ROOT / "fixture_mark.html").resolve().as_uri()
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


HIDDEN = "(id) => { const el = document.getElementById(id); return !el || el.getClientRects().length === 0 }"


def open_page(browser, seed=None):
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)[:200]))
    if seed:
        page.add_init_script("window.__SEED = %s" % json.dumps(seed))
    page.goto(FIXTURE)
    page.add_script_tag(content=CONTENT)
    page.wait_for_timeout(200)
    return page, errors


def mark(page, post_id):
    """What the owner does: circle → Mark an ad… → tap the post."""
    page.click("#echolike-lite-fab .dot")
    page.wait_for_timeout(120)
    page.click("#echolike-lite-fab .panel button[data-act='markad']")
    page.wait_for_timeout(120)
    page.click("#" + post_id)
    page.wait_for_timeout(200)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # 1. The word is unknown, so nothing is hidden — the reported situation.
    page, errors = open_page(browser)
    check("the unknown word hides nothing", page.evaluate(HIDDEN, "ad1"), False)
    check("and no page errors", errors, [])

    # 2. One mark: gone now, reported, and the word kept as a candidate (not learned:
    #    one mark cannot tell a disclosure from an advertiser's own name).
    mark(page, "ad1")
    check("the marked ad is hidden immediately", page.evaluate(HIDDEN, "ad1"), True)
    store = page.evaluate("window.__store()")
    check("its words are held as candidates", len(store["ads_pending"]) > 0, True)
    check("nothing is learned from one mark", store["ads_learned"], [])
    marks = [m for m in page.evaluate("window.__tel") if m.get("action") == "ads.mark"]
    check("the mark reported its shape", len(marks), 1)
    detail = (marks[0].get("info") or {}).get("detail", "")
    check("the report names the card, not its text", "words=[h=" in detail and "Annonce" not in detail, True)
    check("and says it is waiting for a second mark", "pending=" in detail, True)
    check("the post itself was not captured as a like",
          [m["type"] for m in page.evaluate("window.__sent") if m["type"] == "capture"], [])
    reports = [m for m in page.evaluate("window.__sent") if m["type"] == "adreport"]
    check("a rich report goes with the mark", len(reports), 1)
    rich = (reports[0].get("report") or {}) if reports else {}
    check("it says it is a mark", rich.get("kind"), "mark")
    check("it carries the card's markup at the default level", len(rich.get("html", "")) > 50, True)
    check("and the candidate words as they are", "Annonce" in rich.get("words", ""), True)
    # The owner sets how much a report may carry; "shapes" sends no words and no markup.
    page.evaluate("window.__setStore({report_level: 'shapes'})")
    page.evaluate("window.__changeListeners.forEach(f => f({report_level: {newValue: 'shapes'}}))")
    mark(page, "ad2")
    reports = [m for m in page.evaluate("window.__sent") if m["type"] == "adreport"]
    shapes = (reports[-1].get("report") or {}) if reports else {}
    check("the 'shapes' level sends no words", shapes.get("words"), "")
    check("and no markup", shapes.get("html"), "")
    page.close()

    # 3. Two marks of the same kind teach the word.
    page = browser.new_page()
    captured = {}
    page.on("pageerror", lambda e: captured.setdefault("errors", []).append(str(e)[:200]))
    page.goto(FIXTURE)
    page.add_script_tag(content=CONTENT)
    page.wait_for_timeout(150)
    mark(page, "ad1")
    pending = page.evaluate("window.__store()")["ads_pending"]
    mark(page, "ad2")
    store = page.evaluate("window.__store()")
    check("the second mark teaches the word", len(store["ads_learned"]) > 0, True)
    check("and it is the word both ads shared", set(pending) & set(store["ads_learned"]) != set(), True)
    check("the candidates are cleared once learned", store["ads_pending"], [])
    check("a real post was never touched", page.evaluate(HIDDEN, "real1"), False)
    check("no page errors while marking", captured.get("errors", []), [])
    learned = store["ads_learned"]
    page.close()

    # 3b. An ad with no disclosure word at all (the first field mark): its SHAPE is
    #     what gets learned, and two marks of the same shape teach it.
    page, errors = open_page(browser)
    check("a label-less ad is not hidden by words", page.evaluate(HIDDEN, "ad3"), False)
    mark(page, "ad3")
    mark(page, "ad4")
    store = page.evaluate("window.__store()")
    check("the shape is learned from two marks", len(store["ads_skel"]), 1)
    check("and the shape candidate is cleared", store["ads_skel_pending"], "")
    check("the ordinary post still has a different shape",
          page.evaluate(HIDDEN, "real1"), False)
    shape = store["ads_skel"]
    check("no page errors while marking shapes", errors, [])
    page.close()

    # 3c. After a reload a learned shape hides the same kind of card, and only that.
    page, errors = open_page(browser, seed={"ads_skel": shape})
    check("the first label-less ad hides on load", page.evaluate(HIDDEN, "ad3"), True)
    check("the second one too", page.evaluate(HIDDEN, "ad4"), True)
    check("the ordinary post stays", page.evaluate(HIDDEN, "real1"), False)
    check("a worded ad of another kind is untouched", page.evaluate(HIDDEN, "ad1"), False)
    page.close()

    # 4. After a reload the learned word hides the ads by itself — no marking needed.
    page, errors = open_page(browser, seed={"ads_learned": learned})
    check("the first ad hides on load", page.evaluate(HIDDEN, "ad1"), True)
    check("the second one too", page.evaluate(HIDDEN, "ad2"), True)
    check("and the ordinary post stays", page.evaluate(HIDDEN, "real1"), False)
    report = page.evaluate("""() => {
      let out = null;
      for (const fn of (window.__msgListeners || [])) fn({ type: "ads-report" }, {}, (r) => { out = r; });
      return out;
    }""")
    check("the report says how many words are learned", (report or {}).get("learned"), len(learned))
    check("no page errors after reload", errors, [])
    page.close()

    browser.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
