"""Capture against x-web, the 2026 X rewrite: no data-testid anywhere.

The failure this pins down: X moved signed-in people to the new app country by
country and every selector in the script was keyed on data-testid, so a like
produced nothing and nothing said so. The rewrite keeps two stable facts — the
icon inside an engagement button and its aria-pressed state — and those are what
this test drives.

    xvfb-run -a python3 tests/review_new_dom.py
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
CONTENT = (ROOT.parent / "extension" / "content.js").read_text()
fixture = ROOT / "fixture_new.html"
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


def captures(page):
    return [m["item"] for m in page.evaluate("window.__sent") if m["type"] == "capture"]


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(fixture.as_uri())
    page.add_script_tag(content=CONTENT)

    # 1. like on a post that quotes another: own id, own text, own counts.
    page.click('#main button[aria-label^="12 Likes"]')
    page.wait_for_timeout(150)
    sent = captures(page)
    check("captures after like", len(sent), 1)
    if sent:
        it = sent[0]
        check("tweet id", it["id"], "111")
        check("handle", it["handle"], "nasa")
        check("kind", it["kind"], "like")
        check("text is the post's own", it["text"], "The real post text.")
        check("lang", it["lang"], "en")
        check("author name", it["author_name"], "NASA")
        check("quoted id kept", it["quotes"], "999")
        check("replies", it["counts"]["replies"], 1234)
        check("reposts", it["counts"]["reposts"], 56)
        check("likes", it["counts"]["likes"], 12)
        check("bookmarks", it["counts"]["bookmarks"], 3)
        check("views", it["counts"]["views"], 98700)
        check("one photo, not the quote's", it["photos"], 1)
        check("no video", it["videos"], 0)
        check("no ad flag", it["ad"], False)
        check("published_at is honest", it["published_at"], None)
        check("published_text carries X's own date", it["published_text"], "Nov 23")
        check("url", it["url"], "https://x.com/nasa/status/111")
        check("source", it["source"], "like")

    # 2. the layout fingerprint went out, and it says x-web.
    tel = page.evaluate("window.__tel || []")
    dom = [m for m in tel if m.get("action") == "dom"]
    check("a dom event was reported", len(dom), 1)
    if dom:
        check("dom says x-web", "layout=x-web" in ((dom[0].get("info") or {}).get("detail") or ""), True)
        check("dom counts the hearts", "hearts=" in ((dom[0].get("info") or {}).get("detail") or ""), True)
    caps = [m for m in tel if m.get("action") == "capture"]
    check("a capture event was reported", len(caps), 1)

    # 3. pressed toggles: the same control now removes, and must be named so.
    page.click('#liked button[aria-label^="5 Likes"]')
    page.click('#liked button[aria-label^="1 Bookmark"]')
    page.wait_for_timeout(150)
    sent = captures(page)
    check("captures after unlike + unbookmark", len(sent), 3)
    if len(sent) == 3:
        check("unlike kind", sent[1]["kind"], "unlike")
        check("unlike id", sent[1]["id"], "222")
        check("unbookmark kind", sent[2]["kind"], "unbookmark")
        check("bookmark count on the unbookmark", sent[2]["counts"]["bookmarks"], 1)

    # 4. the quote's own heart captures the quote, with its own id.
    page.click('#quote button[aria-label^="9 Likes"]')
    page.wait_for_timeout(150)
    sent = captures(page)
    if len(sent) == 4:
        check("quote id", sent[3]["id"], "999")
        check("quote handle", sent[3]["handle"], "someoneelse")
        check("quote text", sent[3]["text"], "Quoted tweet text that must be ignored.")

    # 5. a renamed icon and a non-<article> row: the label and role=article carry it.
    page.click('#rolepost button[aria-label^="8 Likes"]')
    page.wait_for_timeout(150)
    sent = captures(page)
    if len(sent) == 5:
        check("label-only like id", sent[4]["id"], "555")
        check("label-only kind", sent[4]["kind"], "like")
        check("role=article text", sent[4]["text"], "A row that is not an article element.")
    page.click('#rolepost button[aria-label="Remove Bookmark"]')
    page.wait_for_timeout(150)
    sent = captures(page)
    if len(sent) == 6:
        check("label-only unbookmark", sent[5]["kind"], "unbookmark")

    # 6. a heart with no post link fails loudly: no invented item, one diagnostic.
    page.click('#nopost button[aria-label^="7 Likes"]')
    page.wait_for_timeout(150)
    check("no capture invented", len(captures(page)), 6)
    tel = page.evaluate("window.__tel || []")
    noitem = [m for m in tel if m.get("action") == "capture.noitem"]
    check("capture.noitem reported", len(noitem), 1)

    # 7. a "Bookmarks" control outside a post is not a capture and not an error.
    page.click('#navbookmark')
    page.wait_for_timeout(100)
    check("nav click captures nothing", len(captures(page)), 6)
    tel = page.evaluate("window.__tel || []")
    check("nav click is not 'noitem'", len([m for m in tel if m.get("action") == "capture.noitem"]), 1)

    # 8. ads: the text-only disclosure x-web prints is enough to hide the cell,
    #    while a real post whose text is "Promoted" stays.
    check("promoted cell hidden", page.is_visible('#promotedcell'), False)
    check("a post that says Promoted stays", page.is_visible('#wordpost'), True)
    check("a normal post stays", page.is_visible('#main'), True)
    page.evaluate("""() => {
      const li = document.createElement('li');
      li.id = 'latecell';
      li.innerHTML = '<div role="link"><article id="latepromoted">' +
        '<div class="flex"><a href="/late"><div class="font-bold" dir="auto">Late</div></a>' +
        '<span>Promocionado por Late</span></div>' +
        '<div dir="auto" lang="en">Another ad, appended later.</div></article></div>';
      document.body.appendChild(li);
    }""")
    page.wait_for_timeout(200)
    check("an ad appended later is hidden by the observer", page.is_visible('#latecell'), False)
    page.evaluate("window.__setHideAds(false)")
    page.wait_for_timeout(100)
    check("switch off brings them back", page.is_visible('#promotedcell'), True)
    check("and the late one too", page.is_visible('#latecell'), True)
    page.evaluate("window.__setHideAds(true)")
    page.wait_for_timeout(100)
    check("switch on hides again", page.is_visible('#promotedcell'), False)

    # 9. the import walk never turns a quoted post into a capture of its own.
    page.evaluate("""() => {
      window.__sent.length = 0;
      window.__msgListeners[0]({ type: 'import-start', mode: 'likes', limit: 2 }, null, () => {});
    }""")
    page.wait_for_timeout(400)
    batch = [m for m in page.evaluate("window.__sent") if m["type"] == "capture-batch"]
    check("one import batch", len(batch), 1)
    if batch:
        ids = [it["id"] for it in batch[0]["items"]]
        check("imported ids", sorted(ids), ["111", "222"])
        check("no quoted post in the walk", "999" in ids, False)

    browser.close()

print()
if failures:
    print("FAILED: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
