"""A backlog must drain itself.

The reported state: `1 in the inbox · 18 in this browser · 17 waiting to send`.
Two ways a queue got stuck, both fixed here and pinned down:

1. the queue was written by a version that had no encryption, so every send hit
   "items must carry iv + ct" (400) and the backlog stayed forever;
2. opening the extension page did nothing, because only a new capture, a restart
   or a Retry press ever triggered a send.

This test seeds a plaintext backlog, connects to the real hosted inbox, opens the
page, and expects the queue to drain and the captures to arrive encrypted.

    bash bin/live-test-reset.sh          # the live tests claim a lot
    xvfb-run -a python3 tests/review_drain.py

Exit code 1 on any failure.
"""
import json
import pathlib
import socket
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ids import extension_id  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = str(ROOT / "extension")
TEXT = "backlog item " + str(int(time.time()))
sock = socket.socket()
sock.bind(("127.0.0.1", 0))
PORT = sock.getsockname()[1]
sock.close()
server_dir = tempfile.mkdtemp(prefix="echolike-lite-drain-srv-")
srv = subprocess.Popen(
    [sys.executable, "-u", str(ROOT / "server.py"), "--port", str(PORT)],
    cwd=server_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
)
for _ in range(50):
    if srv.stdout.readline().startswith("EchoLike Lite inbox on"):
        break
HOST = "http://127.0.0.1:%d" % PORT
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


prof = tempfile.mkdtemp(prefix="echolike-lite-drain-")
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        prof, headless=False,
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-first-run"],
    )
    try:
        page = ctx.new_page()
        page.on("pageerror", lambda e: print("PAGEERROR", str(e)[:200]))
        page.goto(f"chrome-extension://{extension_id()}/app.html#inbox")
        page.wait_for_timeout(600)

        # A backlog written by an older version: plaintext, no iv/ct, in the outbox.
        old = [
            {"uid": "old-1", "kind": "like", "id": "501", "handle": "nasa",
             "url": "https://x.com/nasa/status/501", "text": TEXT, "clicked_at": "2026-11-12T00:00:00Z"},
            {"uid": "old-2", "kind": "bookmark", "id": "502", "handle": "sama",
             "url": "https://x.com/sama/status/502", "text": TEXT + " b", "clicked_at": "2026-11-12T00:01:00Z"},
        ]
        page.evaluate("items => chrome.storage.local.set({items, outbox: items})", old)
        page.reload()
        page.wait_for_timeout(600)
        check("the backlog is visible before connecting", "waiting" in page.inner_text("#status"), True)

        # Connect through Settings (pasting the address, no discovery races): the
        # claim itself must send what is queued.
        page.goto(f"chrome-extension://{extension_id()}/app.html#settings")
        page.wait_for_timeout(600)
        page.fill("#url", HOST)
        page.click("#save")
        page.wait_for_timeout(5000)
        check("connected", page.evaluate("chrome.storage.local.get({url:''}).then(s=>s.url)"), HOST)
        pending = page.evaluate("chrome.storage.local.get({outbox:[]}).then(s=>s.outbox.length)")
        check("the plaintext backlog drained", pending, 0)
        check("nothing says it is still waiting", "waiting to send" in page.inner_text("#status"), False)

        # What arrived must be ciphertext the inbox cannot read.
        stored = (pathlib.Path(server_dir) / "likes.jsonl").read_text()
        check("the inbox holds the old captures as blobs", stored.count('"ct"') >= 2, True)
        check("and cannot read them", "backlog item" in stored, False)

        # Back to the inbox tab by clicking it, as a user does.
        page.click("#tab-inbox")
        page.wait_for_timeout(3000)
        check("still nothing pending", page.evaluate("chrome.storage.local.get({outbox:[]}).then(s=>s.outbox.length)"), 0)
        line = page.inner_text("#status")
        print("   telemetry:", json.dumps(page.evaluate("chrome.storage.local.get({telemetry:[]}).then(s=>s.telemetry.slice(-6))"), indent=1)[:700])
        print("   status:", line.replace("\n", " "))
        check("status counts them", "in the inbox" in line, True)
        check("and shows the words after decrypting", TEXT in page.inner_text("#list"), True)
        check("the queue did not come back", page.evaluate("chrome.storage.local.get({outbox:[]}).then(s=>s.outbox.length)"), 0)

        # The repair path: the mirror holds captures that never made it (the old
        # flush race, or a queue cleared by an older version). One button sends them.
        orphans = [
            {"uid": "oph-1", "kind": "like", "id": "601", "handle": "esa",
             "url": "https://x.com/esa/status/601", "text": TEXT + " orphan 1", "clicked_at": "2026-11-12T00:02:00Z"},
            {"uid": "oph-2", "kind": "like", "id": "602", "handle": "esa",
             "url": "https://x.com/esa/status/602", "text": TEXT + " orphan 2", "clicked_at": "2026-11-12T00:03:00Z"},
        ]
        page.evaluate("items => chrome.storage.local.get({items:[], outbox:[]}).then(s => chrome.storage.local.set({items: s.items.concat(items), outbox: s.outbox}))", orphans)
        page.reload()
        page.wait_for_timeout(2500)
        check("the mirror notices what the inbox lacks", "not in the inbox" in page.inner_text("#status"), True)
        page.click("#retry")
        page.wait_for_timeout(4000)
        stored = (pathlib.Path(server_dir) / "likes.jsonl").read_text()
        check("the missing ones were re-sent", stored.count('"ct"') >= 4, True)
        check("and none of their words leaked", "orphan" in stored, False)
        check("nothing is missing any more", "not in the inbox" in page.inner_text("#status"), False)
    finally:
        ctx.close()
        srv.terminate()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
