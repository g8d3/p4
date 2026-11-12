"""Account, from the user's seat: email code, signed in, key backed up, key restored.

Drives the real popup against a LOCAL worker (`wrangler dev --local`, ECHO_DEV_CODE=1
so the code comes back instead of being mailed; production never does that).

    cd inbox-worker && wrangler dev --port 8788 --local --compatibility-date 2026-10-30
    xvfb-run -a python3 tests/review_account_ui.py

Exit code 1 on any failure.
"""
import json
import pathlib
import sys
import tempfile
import urllib.request

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ids import extension_id  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = str(ROOT / "extension")
BASE = "http://127.0.0.1:8788"
EMAIL = "seat-%d@example.com" % __import__("random").randint(1000, 9999)
PHRASE = "the horse battery staple"
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


try:
    urllib.request.urlopen(BASE + "/api/health", timeout=5)
except Exception as e:
    print("worker is not running on", BASE, "->", e)
    print("FAILURES: ['worker']")
    sys.exit(1)

prof = tempfile.mkdtemp(prefix="echolike-lite-acct-")
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        prof, headless=False,
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-first-run"],
    )
    try:
        page = ctx.new_page()
        page.on("pageerror", lambda e: print("PAGEERROR", str(e)[:200]))
        page.on("dialog", lambda d: d.accept())
        page.goto(f"chrome-extension://{extension_id()}/popup.html")
        page.wait_for_timeout(500)

        # Settings page: connect to the local worker with an address only (it mints the token).
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())
        page.on("pageerror", lambda e: print("PAGEERROR", str(e)[:200]))
        page.goto(f"chrome-extension://{extension_id()}/options.html")
        page.wait_for_timeout(600)
        page.fill("#url", BASE)
        page.click("#save")
        page.wait_for_timeout(2000)
        check("connected to the local inbox", "Connected" in page.inner_text("#inboxstatus"), True)

        # Ask for a code (the dev worker hands it back), then type it in the UI.
        start = page.evaluate(
            "async (email) => await chrome.runtime.sendMessage({type:'acct-start', email})", EMAIL
        )
        check("a code was issued", start.get("ok"), True)
        code = str(start.get("code") or "")
        check("six digits", len(code), 6)

        page.fill("#email", EMAIL)
        page.fill("#code", code)
        page.click("#verify")
        page.wait_for_timeout(2000)
        status = page.evaluate("document.getElementById('acctstatus').textContent")
        check("signed in", "Signed in as" in status, True)
        check("email shown", EMAIL in page.evaluate("document.getElementById('acctstatus').textContent"), True)
        check("account token stored", page.evaluate("chrome.storage.local.get({accountToken:''}).then(s=>s.accountToken.length)"), 32)

        key_before = page.evaluate("chrome.storage.local.get({key:''}).then(s=>s.key)")
        check("a local key exists", len(key_before), 43)

        # Back the key up (wrapped with the passphrase here, never sent in the clear).
        page.fill("#phrase", PHRASE)
        page.click("#backup")
        page.wait_for_timeout(4000)
        check("backup reported", "backed up" in page.inner_text("#acctmsg").lower(), True)

        atoken = page.evaluate("chrome.storage.local.get({accountToken:''}).then(s=>s.accountToken)")
        req = urllib.request.Request(
            BASE + "/api/account/key",
            headers={"authorization": "Bearer " + atoken, "content-type": "application/json"},
        )
        backup = json.loads(urllib.request.urlopen(req, timeout=10).read())
        blob = json.dumps(backup)
        check("the server holds a wrapped blob", "backup" in backup and bool(backup["backup"].get("ct")), True)
        check("the server never sees the key", key_before in blob or PHRASE in blob, False)

        # Simulate a new device: a different key, then restore with the passphrase.
        page.evaluate("chrome.storage.local.set({key: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'})")
        page.fill("#phrase", "wrong passphrase")
        page.click("#restore")
        page.wait_for_timeout(4000)
        check("a wrong passphrase is refused", "wrong passphrase" in page.inner_text("#acctmsg").lower(), True)
        check("and the key is untouched", page.evaluate("chrome.storage.local.get({key:''}).then(s=>s.key)") != key_before, True)

        page.fill("#phrase", PHRASE)
        page.click("#restore")
        page.wait_for_timeout(4000)
        page.reload()
        page.wait_for_timeout(800)
        check("the right passphrase restores the key", page.input_value("#key"), key_before)
        # #acctstatus lives inside the folded Advanced block: read its text, not its layout.
        check("account shown after reload", EMAIL in page.evaluate("document.getElementById('acctstatus').textContent"), True)
    finally:
        ctx.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
