"""End-to-end: real Chrome with the extension + the real server.py.

Connect from the popup, send a capture through the same channel the content
script uses, and check the server stored it. No mocks on either side.
"""
import json
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ids import extension_id  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = str(ROOT / "extension")
server_dir = tempfile.mkdtemp(prefix="echolike-lite-srv-")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


PORT = free_port()
srv = subprocess.Popen(
    [sys.executable, "-u", str(ROOT / "server.py"), "--port", str(PORT)],
    cwd=server_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
)
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


try:
    token = None
    for _ in range(50):
        line = srv.stdout.readline()
        if line.startswith("Token: "):
            token = line.split()[1].strip()
            break
    check("server printed a token", len(token or ""), 32)

    prof = tempfile.mkdtemp(prefix="echolike-lite-prof-")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            prof, headless=False,
            args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-first-run"],
        )
        eid = extension_id()
        page = ctx.new_page()
        page.on("pageerror", lambda e: print("PAGEERROR", str(e)[:200]))
        page.goto(f"chrome-extension://{eid}/popup.html")
        page.wait_for_timeout(400)
        opts = ctx.new_page()
        opts.goto(f"chrome-extension://{eid}/app.html#settings")
        opts.wait_for_timeout(400)

        url = f"http://127.0.0.1:{PORT}"
        # Claim path: address only, no token typed. The server mints the device token.
        # Settings page: address only, no token typed. The server mints the device token.
        opts.fill("#url", url)
        opts.click("#save")
        opts.wait_for_timeout(1800)
        check("claim with no token reports connected", "Connected" in opts.inner_text("#inboxstatus"), True)
        check("settings says connected", "Connected" in opts.inner_text("#inboxstatus"), True)
        check(
            "device token stored",
            len(opts.evaluate("chrome.storage.local.get({token:''}).then(s=>s.token)")),
            32,
        )

        # Same message shape content.js sends.
        reply = page.evaluate(
            """async () => await chrome.runtime.sendMessage({type:'capture', item:{
                 kind:'like', id:'777', handle:'nasa', url:'https://x.com/nasa/status/777',
                 text:'e2e capture', tweet_time:null, clicked_at:new Date().toISOString()}})"""
        )
        check("capture acknowledged as sent", reply.get("sent"), True)

        page.wait_for_timeout(400)
        page.reload()
        page.wait_for_timeout(500)
        rows = page.query_selector_all("#list div")
        check("one row in the popup list", len(rows), 1)
        check("row text", "e2e capture" in (rows[0].inner_text() if rows else ""), True)
        check("nothing left pending", page.evaluate("chrome.storage.local.get({outbox:[]}).then(s=>s.outbox.length)"), 0)

        # The server must hold the capture — and must not be able to read one word of it.
        log = pathlib.Path(server_dir) / "likes.jsonl"
        stored = log.read_text() if log.exists() else ""
        check("server stored a blob", '"ct"' in stored, True)
        check("the words never left the browser", "e2e capture" in stored, False)
        check("nor the handle", "nasa" in stored, False)
        html = urllib.request.urlopen(url + "/", timeout=5).read().decode()
        check("server page says it cannot read them", "cannot read" in html, True)
        check("server page counts it", "1 capture" in html, True)

        # Token wrong -> the settings page must say so and keep the item for retry.
        # (Paste path: a hosted inbox or another machine still hands out its own token.)
        opts.fill("#url", url)
        opts.fill("#token", "0" * 32)
        opts.click("#save")
        opts.wait_for_timeout(1500)
        check("bad token reported", "401" in opts.inner_text("#inboxstatus"), True)
        check("nothing was lost", page.evaluate("chrome.storage.local.get({items:[]}).then(s=>s.items.length)"), 1)
        ctx.close()
finally:
    srv.terminate()
    try:
        srv.wait(timeout=5)
    except subprocess.TimeoutExpired:
        srv.kill()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
