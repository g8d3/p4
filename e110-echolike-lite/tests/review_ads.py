"""Ads toggle: promoted posts and promoted trends go away — Grok answers and real
posts never do. Real browser, the real content script, X-shaped markup.

The bug this pins down: X puts Grok answer modules in the same
[data-testid="placementTracking"] wrapper as ads, so hiding every placement also
erased Grok's answers. A placement is an ad only if it holds a tweet and shows no
Grok marker.
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
CONTENT = (ROOT.parent / "extension" / "content.js").read_text()
fixture = ROOT / "fixture.html"

failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


HIDDEN = "(id) => { const el = document.getElementById(id); return !!el && el.getClientRects().length === 0 }"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(fixture.as_uri())
    page.add_script_tag(content=CONTENT)
    page.wait_for_timeout(150)

    def hidden(i):
        return page.evaluate(HIDDEN, i)

    # Switch on (the default): ads out, everything X actually shows stays.
    check("promoted post cell hidden", hidden("adcell"), True)
    check("promoted post article hidden with it", hidden("adarticle"), True)
    check("promoted trend hidden", hidden("promotedtrend"), True)
    check("Grok answer module visible", hidden("grokmodule"), False)
    check("Grok answer as a post visible", hidden("grokarticle"), False)
    check("its cell visible", hidden("grokTweetCell"), False)
    check("real trend visible", hidden("normaltrand"), False)

    # Switch off: nothing is hidden at all.
    page.evaluate("window.__setHideAds(false)")
    page.wait_for_timeout(150)
    check("ads back when switched off", hidden("adcell"), False)
    check("promoted trend back", hidden("promotedtrend"), False)

    # And on again, so the toggle is reversible in both directions.
    page.evaluate("window.__setHideAds(true)")
    page.wait_for_timeout(150)
    check("ads hidden again", hidden("adcell"), True)
    check("Grok still visible after toggling", hidden("grokmodule"), False)

    browser.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
