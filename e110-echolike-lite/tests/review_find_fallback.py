"""Find my inbox must not stop at the first refusal.

The failure that made the owner press a button and get nothing: his own inbox on
port 8931 answered /api/health but refused the claim (device limit), so discovery
aborted instead of falling through to the hosted inbox that was right there.

Reproduce it exactly: a local inbox that is alive and refuses, on the port the
extension probes first, plus the real hosted inbox behind it.

    systemctl --user stop echolike-lite-inbox          # free port 8931
    xvfb-run -a python3 tests/review_find_fallback.py
    systemctl --user start echolike-lite-inbox

Exit code 1 on any failure.
"""
import pathlib
import socket
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ids import extension_id  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = str(ROOT / "extension")
HOST = "https://inbox-lite.echolike.app"
refuser_dir = tempfile.mkdtemp(prefix="echolike-lite-refuser-")
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


probe = socket.socket()
try:
    probe.bind(("127.0.0.1", 8931))
    probe.close()
except OSError:
    print("port 8931 is busy: stop the inbox unit first (systemctl --user stop echolike-lite-inbox)")
    print("FAILURES: ['port']")
    sys.exit(1)

# A live inbox that will refuse everybody: --max-devices 0.
refuser = subprocess.Popen(
    [sys.executable, "-u", str(ROOT / "server.py"), "--port", "8931", "--max-devices", "0"],
    cwd=refuser_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
try:
    for _ in range(50):
        if refuser.stdout.readline().startswith("EchoLike Lite inbox on"):
            break
    prof = tempfile.mkdtemp(prefix="echolike-lite-fb-")
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
            page.click("#find")
            page.wait_for_timeout(6000)
            url = page.evaluate("chrome.storage.local.get({url:''}).then(s=>s.url)")
            check("it did not stop at the refusing local inbox", url, HOST)
            status = page.inner_text("#status")
            check("the page says which inbox it chose", "inbox-lite.echolike.app" in status, True)
            check("the button is out of the way", page.is_visible("#find"), False)
            check(
                "a device token for the hosted inbox",
                len(page.evaluate("chrome.storage.local.get({token:''}).then(s=>s.token)")),
                32,
            )
        finally:
            ctx.close()
finally:
    refuser.terminate()
    try:
        refuser.wait(timeout=5)
    except subprocess.TimeoutExpired:
        refuser.kill()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
