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

        # First run: nothing to type. One button, Advanced folded away.
        print("find button:", page.inner_text("#find"), "| visible:", page.is_visible("#find"))
        print("advanced folded by default:", not page.is_visible("#url"))
        page.click("#find")
        page.press("#find", "Enter")  # Enter on a focused button must not double-fire
        page.wait_for_timeout(3000)
        print("after Find my inbox:", page.inner_text("#status").replace("\n", " "))

        # Connect flow against no server: must report a clean error, not hang.
        page.click("#adv summary")
        page.wait_for_timeout(150)
        page.fill("#url", "http://127.0.0.1:59999")
        page.fill("#token", "deadbeef")
        page.click("#save")
        page.wait_for_timeout(2500)
        print("after bad connect:", page.inner_text("#status").replace("\n", " "))
        print("token field cleared:", page.input_value("#token") == "")
        print("items kept:", page.evaluate("chrome.storage.local.get({items:[]}).then(s=>s.items.length)"))
    finally:
        ctx.close()
