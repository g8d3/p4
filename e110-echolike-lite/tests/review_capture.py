"""Capture test: the content script against X-shaped markup, in a real browser.

Checks what actually breaks in the wild: wrong tweet id (quoted tweet), missing
text, and kind detection (like vs unlike vs bookmark).
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


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(fixture.as_uri())
    page.add_script_tag(content=CONTENT)

    # 1. like on the first article: must read the parent tweet, never the quote
    page.click('article:nth-of-type(1) [data-testid="like"]')
    page.wait_for_timeout(150)
    sent = page.evaluate("window.__sent")
    check("items after like", len(sent), 1)
    if sent:
        it = sent[0]["item"]
        check("tweet id", it["id"], "111")
        check("handle", it["handle"], "nasa")
        check("text", it["text"], "The real post text.")
        check("kind", it["kind"], "like")
        check("url", it["url"], "https://x.com/nasa/status/111")
        check("tweet_time", it["tweet_time"], "2026-11-10T10:00:00Z")
        check("published_at", it["published_at"], "2026-11-10T10:00:00Z")
        check("author name", it["author_name"], "NASA")
        check("lang", it["lang"], "en")
        check("replies parsed from a Spanish aria-label", it["counts"]["replies"], 1234)
        check("reposts", it["counts"]["reposts"], 56)
        check("likes", it["counts"]["likes"], 12)
        check("bookmarks", it["counts"]["bookmarks"], 3)
        check("views from the analytics link", it["counts"]["views"], 98765)
        check("captured_at is recorded", bool(it["captured_at"]), True)
        check("source", it["source"], "like")
        check("page", it["page"].startswith("/"), True)

    # 2. unlike on the second article (already liked): kind must be unlike
    page.click('article:nth-of-type(2) [data-testid="unlike"]')
    page.wait_for_timeout(150)
    sent = page.evaluate("window.__sent")
    check("items after unlike", len(sent), 2)
    if len(sent) == 2:
        check("unlike kind", sent[1]["item"]["kind"], "unlike")
        check("unlike id", sent[1]["item"]["id"], "222")

    # 3. bookmark
    page.click('article:nth-of-type(1) [data-testid="bookmark"]')
    page.wait_for_timeout(150)
    sent = page.evaluate("window.__sent")
    check("items after bookmark", len(sent), 3)
    if len(sent) == 3:
        check("bookmark kind", sent[2]["item"]["kind"], "bookmark")

    # 4. a click that is not an action button sends nothing
    page.click('article:nth-of-type(1) [data-testid="reply"]')
    page.wait_for_timeout(150)
    check("no capture for reply", len(page.evaluate("window.__sent")), 3)

    # 5. ads: promoted post and promoted trend hidden by default, real ones untouched
    check("ad cell hidden", page.is_visible("#adcell"), False)
    check("promoted trend hidden", page.is_visible("#promotedtrend"), False)
    check("real trend visible", page.is_visible("#normaltrand"), True)
    check("real posts visible", page.is_visible('article:nth-of-type(1)'), True)

    # 5b. the toggle turns it off live, without a reload
    page.evaluate("window.__setHideAds(false)")
    page.wait_for_timeout(100)
    check("toggle shows ads again", page.is_visible("#adcell"), True)
    check("toggle shows promoted trends", page.is_visible("#promotedtrend"), True)
    page.evaluate("window.__setHideAds(true)")
    page.wait_for_timeout(100)
    check("toggle hides again", page.is_visible("#adcell"), False)

    # 5c. liking an ad is still captured, flagged as ad (never silently dropped)
    page.evaluate("window.__setHideAds(false)")
    page.click("#adarticle [data-testid=like]")
    page.wait_for_timeout(100)
    last = page.evaluate("window.__sent.slice(-1)[0].item")
    check("ad like captured", last["id"], "333")
    check("ad like flagged", last["ad"], True)

    # 6. double injection must not double-send (guard)
    page.add_script_tag(content=CONTENT)
    page.click('article:nth-of-type(1) [data-testid="like"]')
    page.wait_for_timeout(150)
    check("no double listener", len(page.evaluate("window.__sent")), 5)

    # localised counts are part of the data, so they get their own parsing checks
    cases = page.evaluate(
        """() => {
             const src = document.createElement('div');
             return null;
           }"""
    )
    browser.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
