"""User seat: install the extension, press one button, nothing else.

The whole point of 1.1.0: a real Chrome with no configuration finds the inbox on
this machine and gets a device token by itself. No address, no token, ever.

Runs inside a throw-away network namespace so port 8931 is free and nothing on
the real machine is touched (the live inbox keeps its data and its devices):

    unshare -rn sh -c 'ip link set lo up; xvfb-run -a python3 tests/review_find.py'

Exit code 1 on any failure.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ids import extension_id  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = str(ROOT / "extension")
server_dir = tempfile.mkdtemp(prefix="echolike-lite-find-")
PORT = 8931  # the extension probes this port first
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


srv = subprocess.Popen(
    [sys.executable, "-u", str(ROOT / "server.py"), "--port", str(PORT)],
    cwd=server_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
try:
    for _ in range(50):
        if srv.stdout.readline().startswith("EchoLike Lite inbox on"):
            break
    prof = tempfile.mkdtemp(prefix="echolike-lite-prof-")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            prof,
            headless=False,
            args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-first-run"],
        )
        try:
            eid = extension_id()
            page = ctx.new_page()
            page.on("pageerror", lambda e: print("PAGEERROR", str(e)[:200]))
            page.goto(f"chrome-extension://{eid}/popup.html")
            page.wait_for_timeout(500)

            status0 = page.inner_text("#status")
            check("nothing configured yet", "Connected" in status0, False)
            check("offers the zero-config path", "Nothing to set up" in status0, True)
            check("no address field shown", page.is_visible("#url"), False)
            check("one button to press", page.inner_text("#find"), "Find my inbox")

            page.click("#find")
            page.wait_for_timeout(2500)
            status = page.inner_text("#status")
            check("one click connects", "Connected" in status, True)
            check("picked the local inbox", "127.0.0.1:8931" in status, True)
            check("no token typed", page.input_value("#token"), "")
            check(
                "device token stored by the extension",
                len(page.evaluate("chrome.storage.local.get({token:''}).then(s=>s.token)")),
                32,
            )

            # Nothing to do on the second press: it must not mint another device.
            page.click("#find")
            page.wait_for_timeout(1500)
            devices = json.loads((pathlib.Path(server_dir) / ".devices.json").read_text())
            check("reconnect does not mint a second device", len(devices), 1)

            reply = page.evaluate(
                """async () => await chrome.runtime.sendMessage({type:'capture', item:{
                     kind:'like', id:'900', handle:'nasa', url:'https://x.com/nasa/status/900',
                     text:'found you with one click', clicked_at:new Date().toISOString()}})"""
            )
            check("capture goes out with no setup", reply.get("sent"), True)
            page.wait_for_timeout(400)
            log = pathlib.Path(server_dir) / "likes.jsonl"
            check("server has it", log.exists() and "found you with one click" in log.read_text(), True)
        finally:
            ctx.close()
finally:
    srv.terminate()
    try:
        srv.wait(timeout=5)
    except subprocess.TimeoutExpired:
        srv.kill()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
