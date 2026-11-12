"""No schedule: the queue and the diagnostics go when an event says so.

The owner's requirement, in his words: "it should not be on a schedule, but as
events happen... but if there is no connection it should be synced when there's
connection", and "if the user enables diagnostics they should be sent
automatically".

This drives both with the only events that exist:
  * a capture (kept when offline, sent by the next event),
  * the browser's own `online` event, which is what "connection came back" means,
  * diagnostics leaving the machine with each action, without any button.

    xvfb-run -a python3 tests/review_online.py
"""
import json
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ids import extension_id  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = str(ROOT / "extension")
TEXT = "offline capture " + str(int(time.time()))
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


sock = socket.socket()
sock.bind(("127.0.0.1", 0))
PORT = sock.getsockname()[1]
sock.close()
server_dir = tempfile.mkdtemp(prefix="echolike-lite-online-")
reqlog = pathlib.Path(server_dir) / "requests.log"
srv = subprocess.Popen(
    [sys.executable, "-u", str(ROOT / "server.py"), "--port", str(PORT)],
    cwd=server_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    env=dict(__import__("os").environ, ECHO_LOG_REQUESTS="1"),
)
# the request log goes to stdout; keep it in a file too
import threading

lines = []


def collect():
    for line in srv.stdout:
        lines.append(line)
        with open(reqlog, "a") as f:
            f.write(line)


threading.Thread(target=collect, daemon=True).start()
for _ in range(100):
    if any("EchoLike Lite inbox on" in l for l in lines):
        break
    time.sleep(0.05)

prof = tempfile.mkdtemp(prefix="echolike-lite-on-")
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        prof, headless=False,
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-first-run"],
    )
    try:
        page = ctx.new_page()
        page.on("pageerror", lambda e: print("PAGEERROR", str(e)[:200]))
        page.goto(f"chrome-extension://{extension_id()}/app.html#settings")
        page.wait_for_timeout(600)
        page.fill("#url", "http://127.0.0.1:%d" % PORT)
        page.click("#save")
        page.wait_for_timeout(2500)
        check("connected", "Connected" in page.inner_text("#inboxstatus"), True)

        # Diagnostics left the machine on their own, with no button pressed. Bounded
        # wait: the flush races the assertion when the loopback server is slow.
        log = ""
        for _ in range(20):
            log = reqlog.read_text() if reqlog.exists() else ""
            if "POST /api/telemetry" in log:
                break
            page.wait_for_timeout(300)
        check("diagnostics were uploaded unprompted", "POST /api/telemetry" in log, True)

        # Offline: the capture is kept, nothing is lost, nothing is a timer.
        ctx.set_offline(True)
        page.wait_for_timeout(300)
        page.evaluate(
            """async (text) => await chrome.runtime.sendMessage({type:'capture', item:{
                 kind:'like', id:'903', handle:'nasa', url:'https://x.com/nasa/status/903',
                 text, clicked_at:new Date().toISOString()}})""",
            TEXT,
        )
        page.wait_for_timeout(1500)
        pending = page.evaluate("chrome.storage.local.get({outbox:[]}).then(s=>s.outbox.length)")
        check("offline: the capture is queued", pending, 1)
        check("offline: nothing reached the inbox", TEXT in (pathlib.Path(server_dir) / "likes.jsonl").read_text() if (pathlib.Path(server_dir) / "likes.jsonl").exists() else False, False)

        # Online: the browser says so, and that event is what flushes everything.
        ctx.set_offline(False)
        page.wait_for_timeout(6000)
        pending_after = page.evaluate("chrome.storage.local.get({outbox:[]}).then(s=>s.outbox.length)")
        check("online: the queue drained by itself", pending_after, 0)
        stored = (pathlib.Path(server_dir) / "likes.jsonl").read_text()
        check("online: the inbox got the capture", stored.count('"ct"') >= 1, True)
        check("and cannot read it", TEXT in stored, False)
        check("the alarms API is not even available (no schedule)", page.evaluate("typeof chrome.alarms"), "undefined")
    finally:
        ctx.close()
        srv.terminate()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
