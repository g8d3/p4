"""User-seat review for EchoLike Lite: load the extension in a real Chrome and
check what a user can actually do in the popup. No mocks of chrome.* APIs."""
import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ids import extension_id  # noqa: E402

EXT = "/home/vuos/code/p4/e110-echolike-lite/extension"
profile = tempfile.mkdtemp(prefix="echolike-lite-prof-")

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        profile,
        headless=False,
        args=[
            f"--disable-extensions-except={EXT}",
            f"--load-extension={EXT}",
            "--no-first-run",
        ],
    )
    try:
        ext_id = extension_id()
        ctx.new_page().goto("about:blank")
        ctx.pages[0].wait_for_timeout(1500)
        print("extension id:", ext_id, "| service worker:", [s.url for s in ctx.service_workers][:1])

        page = ctx.new_page()
        page.goto(f"chrome-extension://{ext_id}/popup.html")
        page.wait_for_timeout(500)
        print("empty state:", page.inner_text("#status"), "|", page.inner_text("#list")[:60])

        # Seed two captures the way the content script would, then reopen the popup.
        seeded = [
            {"uid": "u1", "kind": "like", "id": "111", "handle": "nasa",
             "url": "https://x.com/nasa/status/111", "text": "We are going back to the Moon.",
             "clicked_at": "2026-11-11T00:00:00Z"},
            {"uid": "u2", "kind": "bookmark", "id": "222", "handle": "sama",
             "url": "https://x.com/sama/status/222", "text": "scaling laws still hold <script>x</script>",
             "clicked_at": "2026-11-11T00:01:00Z"},
        ]
        page.evaluate(
            "items => chrome.storage.local.set({items, outbox: items})", seeded
        )
        page.reload()
        page.wait_for_timeout(600)
        print("status with backlog:", page.inner_text("#status").replace("\n", " "))
        rows = page.query_selector_all("#list div")
        print("list rows:", len(rows))
        for r in rows:
            print("  -", r.inner_text().replace("\n", " | "))
        # XSS check: the seeded <script> must be text, never an element.
        print("script injected:", page.query_selector("#list script") is not None)

        # Ads toggle: on by default, and it writes what the content script reads.
        check_ads = page.is_checked("#ads")
        print(("  ok   " if check_ads else "  FAIL ") + "ads hidden by default: " + repr(check_ads))
        page.uncheck("#ads")
        page.wait_for_timeout(200)
        stored = page.evaluate("chrome.storage.local.get({hide_ads:true}).then(s=>s.hide_ads)")
        print(("  ok   " if stored is False else "  FAIL ") + "uncheck writes storage: " + repr(stored))
        page.reload()
        page.wait_for_timeout(400)
        print(("  ok   " if not page.is_checked("#ads") else "  FAIL ") + "state survives reload: " + repr(page.is_checked("#ads")))
        page.check("#ads")
        page.wait_for_timeout(200)

        # The popup is status + one button + the list. No settings fields at all.
        print("find button:", page.inner_text("#find"), "| visible:", page.is_visible("#find"))
        print("no url field in the popup:", page.query_selector("#url") is None)
        print("no token field in the popup:", page.query_selector("#token") is None)
        print("no recovery code in the popup:", page.query_selector("#key") is None)
        print("settings button:", page.inner_text("#settings"))
        page.click("#find")
        page.press("#find", "Enter")  # Enter on a focused button must not double-fire
        page.wait_for_timeout(3000)
        print("after Find my inbox:", page.inner_text("#status").replace("\n", " "))

        # The settings page: three cards, one message line each, connect against no server.
        opts = ctx.new_page()
        opts.goto(f"chrome-extension://{ext_id}/app.html#settings")
        opts.wait_for_timeout(600)
        print("settings inbox line:", opts.inner_text("#inboxstatus").replace("\n", " "))
        print("settings cards:", [opts.inner_text(f"section:nth-of-type({i}) h2") for i in (1, 2, 3)])
        print("opened on the settings tab:", opts.is_visible("#url"), "| hash:", opts.evaluate("location.hash"))
        opts.click("#tab-inbox")
        opts.wait_for_timeout(200)
        print("inbox tab shows the list:", opts.is_visible("#list"), "| settings hidden:", not opts.is_visible("#url"),
              "| hash:", opts.evaluate("location.hash"))
        opts.click("#tab-settings")
        opts.wait_for_timeout(200)
        print("back to settings:", opts.is_visible("#url"))
        print("passphrase field is a password:", opts.get_attribute("#phrase", "type"))
        print("recovery code hidden by default:", opts.get_attribute("#key", "type"))
        # Where "Open my inbox" points: the web reader for the hosted inbox, the
        # extension page for an inbox on your own machine. Seeded, so no claim.
        opts.evaluate("""chrome.storage.local.set({
            url: 'https://inbox-lite.echolike.app', token: 'a'.repeat(32), key: 'k'.repeat(43)})""")
        page.reload()
        page.wait_for_timeout(700)
        href = page.evaluate("document.getElementById('open').href")
        print("hosted inbox -> open link:", href.split("#")[0], "| fragment keys:", sorted(href.split("#")[1].split("&")[0].split("=")[0:2]))
        print("label names the site:", "echolike.app" in page.inner_text("#open"))
        opts.evaluate("""chrome.storage.local.set({url: 'http://127.0.0.1:8931', token: 'b'.repeat(32)})""")
        page.reload()
        page.wait_for_timeout(700)
        print("own server -> open link:", page.evaluate("document.getElementById('open').href"))
        opts.evaluate("chrome.storage.local.remove(['url','token','key'])")

        opts.fill("#url", "http://127.0.0.1:59999")
        opts.fill("#token", "deadbeef")
        opts.click("#save")
        opts.wait_for_timeout(2500)
        print("after bad connect:", opts.inner_text("#inboxstatus").replace("\n", " "))
        print("token field cleared:", opts.input_value("#token") == "")
        print("items kept:", opts.evaluate("chrome.storage.local.get({items:[]}).then(s=>s.items.length)"))
    finally:
        ctx.close()
