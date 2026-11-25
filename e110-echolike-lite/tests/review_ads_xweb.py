"""Ads on x-web (X's 2026 rewrite), where there is no marker to match — only text.

The product runs on a phone (the crx is installed in a mobile browser), and the phone
says "Ad", not "Promoted": 1.20.1's list of disclosure words hid nothing there, so the
owner kept seeing ads with the switch on. This pins the properties that must hold
whatever X's markup does next:

  * a disclosure word anywhere in the post's header hides the post — `div` or `span`,
    inside the advertiser's link or not, before or after the post's text, and whether
    it lands with the post or a moment later;
  * a real post that *says* "Ad" or "Promoted by …" as its own text is never hidden,
    and neither is a post that only quotes one;
  * Grok is never hidden;
  * the switch is reversible, and the report the page sends names the shape it saw
    (structure only — it is what fixes the next DOM change from a phone).

    xvfb-run -a python3 tests/review_ads_xweb.py
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
CONTENT = (ROOT.parent / "extension" / "content.js").read_text()
fixture = ROOT / "fixture_ads_xweb.html"

failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


HIDDEN = "(id) => { const el = document.getElementById(id); return !el || el.getClientRects().length === 0 }"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(fixture.as_uri())
    page.add_script_tag(content=CONTENT)
    page.wait_for_timeout(150)

    def hidden(i):
        return page.evaluate(HIDDEN, i)

    # The phone's own wording, a bare "Ad" in a div inside a cellInnerDiv.
    check("the phone's \"Ad\" hides the post's cell", hidden("adcell"), True)
    check("and the post with it", hidden("adarticle"), True)

    # The phone's own shape, as the first `ads.report` documented it: the word plus icon
    # wrappers (one word, two children) — 1.21.0's leaf-only rule missed this.
    check("a label carrying icon wrappers hides its cell", hidden("iconadcell"), True)
    check("and the article inside it", hidden("iconadarticle"), True)

    # The word with decoration around it: "Ad ·" must count as the same word.
    check("a decorated disclosure (\"Ad ·\") hides the post", hidden("decoratedarticle"), True)
    # A sponsored module that is not a post at all: the cell is the unit.
    check("a sponsored module with no post is hidden", hidden("modulecell"), True)

    # "Promoted by <advertiser>", label inside the advertiser's link, article with no cell.
    check("\"Promoted by X\" hides it, link and all", hidden("promotedbyarticle"), True)

    # Real posts that use the same words are not ads.
    check("a real post whose whole text is \"Ad\" stays", hidden("realadarticle"), False)
    check("a real post saying \"Promoted by my friend\" stays", hidden("talker"), False)
    check("a post that only quotes an \"Ad\" stays", hidden("quoter"), False)
    check("a person whose name is \"Ad\" (bold) stays", hidden("personadarticle"), False)
    check("its quoted article is not hidden either", hidden("quoted"), False)

    # Grok shares the old app's ad wrapper.
    check("Grok answers stay visible", hidden("grokcell"), False)

    # The disclosure that arrives after the post is already in the DOM.
    page.evaluate("window.__lateAd()")
    page.wait_for_timeout(400)
    check("an ad whose label paints late is still hidden", hidden("latearticle"), True)

    # What the page reports when the owner presses the button in Settings: structure,
    # never the text, never the handle.
    report = page.evaluate("""() => {
      let out = null;
      for (const fn of (window.__msgListeners || []))
        fn({ type: "ads-report" }, {}, (r) => { out = r; });
      return out;
    }""")
    check("the report names the layout", report and report["layout"], "rweb")  # the Grok cell still carries data-testid
    check("the report counts what is marked", (report or {}).get("marked"), 6)
    check("the report describes the posts it saw", len((report or {}).get("rows", [])), 6)
    check("the report describes modules too", len((report or {}).get("mods", [])) > 0, True)
    blob = str(report)
    check("the report carries no post text", "Buy this" in blob or "hello, my name" in blob, False)
    check("the report carries no handle", "@someone" in blob or "@decor" in blob, False)
    check("short texts travel as fingerprints, not words", "Sponsored" in blob or "Promoted" in blob, False)
    check("and those fingerprints are there", "h=" in blob, True)

    # Off: everything back, nothing marked.
    page.evaluate("window.__setHideAds(false)")
    page.wait_for_timeout(200)
    check("switch off brings the ads back", hidden("adcell"), False)
    check("and the one with the late label", hidden("latearticle"), False)
    check("and clears every mark", page.evaluate("document.querySelectorAll('[data-echolike-ad]').length"), 0)

    # On again: reversible in both directions.
    page.evaluate("window.__setHideAds(true)")
    page.wait_for_timeout(200)
    check("switch on hides them again", hidden("adcell"), True)
    check("Grok still visible after toggling", hidden("grokcell"), False)

    browser.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
