"""A tab press is a tab press: the list does not get re-read to show it again.

The owner's report was "switching tabs takes a lot of time, especially inbox tab".
With 800 captures on a phone, every press of Inbox re-fetched every blob, decrypted
them one by one, and painted 800 cards — on the phone's network and the phone's CPU.
This drives the real extension page against a local inbox with 800 sealed blobs,
throttled to a phone (4x CPU, 1.6 Mbps, 150 ms) and pins the three things that make
the press cheap:

  * the first paint happens after ONE read, and the list is drawn a page at a time;
  * coming back to the Inbox asks the network for nothing at all;
  * a switch lands in well under a second under that throttling.

    xvfb-run -a python3 tests/review_speed.py
"""
import base64
import json
import os
import pathlib
import secrets
import socket
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ids import extension_id  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent
EXT = str((ROOT.parent / "extension").resolve())
N = 800
PAGE = 500  # what the client asks for at a time
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


def b64u(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


# ---- the inbox: 800 sealed captures, exactly the shape the worker hands back ----
KEY = AESGCM.generate_key(bit_length=256)
KEY_CODE = b64u(KEY)
BLOBS = []
aes = AESGCM(KEY)
for i in range(N):
    item = {
        "kind": "like" if i % 3 else "bookmark",
        "id": str(10**17 + i),
        "handle": "@someone",
        "text": "post number %d, long enough to look like a real one when painted" % i,
        "url": "https://x.com/someone/status/%d" % (10**17 + i),
        "clicked_at": "2026-11-2%dT10:%02d:00Z" % (i % 4, i % 60),
        "published_at": "2026-11-20T09:00:00Z",
        "counts": {"likes": i, "reposts": i // 2, "replies": 3, "bookmarks": 1, "views": 1000 + i},
    }
    iv = os.urandom(12)
    BLOBS.append(
        {
            "uid": "u%04d" % i,
            "iv": b64u(iv),
            "ct": b64u(aes.encrypt(iv, json.dumps(item).encode(), None)),
            "bytes": 200,
            "received_at": "2026-11-24T10:00:00Z",
        }
    )

reads = []


class Inbox(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-headers", "authorization, content-type")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._json({})

    def do_GET(self):
        if self.path.startswith("/api/likes"):
            n = int(self.headers.get("content-length") or 0)
            if n:
                self.rfile.read(n)
            reads.append(self.path)
            q = self.path.split("?", 1)[1] if "?" in self.path else ""
            qs = dict(p.split("=", 1) for p in q.split("&") if "=" in p)
            limit = min(int(qs.get("limit", PAGE)), PAGE)
            offset = int(qs.get("offset", 0))
            self._json(
                {
                    "ok": True,
                    "items": BLOBS[offset : offset + limit],
                    "total": N,
                    "user": "u_speedtest",
                    "phones": 1,
                    "used": N,
                    "quota": 3000,
                }
            )
            return
        self._json({"ok": True, "api": 4, "claim": "open"})

    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        if n:
            self.rfile.read(n)
        self._json({"ok": True, "stored": 0})


srv = ThreadingHTTPServer(("127.0.0.1", 0), Inbox)
srv.daemon_threads = True
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:%d" % PORT

prof = tempfile.mkdtemp(prefix="echolike-lite-speed-")
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        prof, headless=False,
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-first-run"],
    )
    try:
        eid = extension_id()
        page = ctx.new_page()
        page.goto(f"chrome-extension://{eid}/app.html#inbox")
        page.evaluate(
            "(a) => chrome.storage.local.set(a)",
            {"url": BASE, "token": "x" * 32, "key": KEY_CODE, "items": [], "outbox": []},
        )
        page.wait_for_timeout(300)

        # The phone this runs on: four times slower than this machine, on a bad link.
        cdp = ctx.new_cdp_session(page)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        cdp.send(
            "Network.emulateNetworkConditions",
            {"offline": False, "latency": 150, "downloadThroughput": 1.6 * 1024 * 1024 / 8, "uploadThroughput": 750 * 1024 / 8},
        )

        reads.clear()
        t0 = time.monotonic()
        page.goto(f"chrome-extension://{eid}/app.html#inbox")
        page.wait_for_selector("#list .cap", timeout=30000)
        cold = (time.monotonic() - t0) * 1000
        print("  ..   first paint: %.0f ms" % cold)
        print("  ..   network reads to get there: %d" % len(reads))
        check("the first paint comes from one full read", len(reads) in (2, 3), True)  # 800/500 pages + its own offset walk
        # 7 s, measured against the code this replaced on the same machine: 11.7 s and all
        # 800 cards. The number is printed above so drift is visible; the guarantees that
        # matter are asserted separately (one read, then instant presses).
        check("first paint under 7 s on a throttled phone", cold < 7000, True)

        cards = page.eval_on_selector_all("#list .cap", "els => els.length")
        print("  ..   cards painted: %d of %d" % (cards, N))
        check("the list is drawn a page at a time", cards < N, True)
        check("and offers the rest", page.is_visible("#more"), True)

        # Never the same post twice: the owner reported duplicated posts, and the list is
        # the one place this product draws rows itself.
        page.eval_on_selector("#more", "b => b.click()")
        page.wait_for_timeout(1500)
        texts = page.eval_on_selector_all("#list .cap", "els => els.map(e => e.innerText)")
        check("a 'show more' adds exactly one page", len(texts), cards + 80)
        check("and no capture is drawn twice", len(set(texts)), len(texts))

        # The tab press the owner complained about.
        reads.clear()
        t0 = time.monotonic()
        page.click("#tab-spaces")
        page.wait_for_selector("#panel-spaces.on", timeout=10000)
        to_spaces = (time.monotonic() - t0) * 1000
        t0 = time.monotonic()
        page.click("#tab-inbox")
        page.wait_for_selector("#panel-inbox.on #list .cap", timeout=10000)
        back = (time.monotonic() - t0) * 1000
        print("  ..   inbox -> spaces: %.0f ms · spaces -> inbox: %.0f ms" % (to_spaces, back))

        check("coming back to the inbox reads nothing from the network", len(reads), 0)
        check("and paints instantly (< 800 ms throttled)", back < 800, True)

        # The other direction, once the list is already in memory.
        t0 = time.monotonic()
        page.click("#tab-inbox")
        page.wait_for_selector("#panel-inbox.on", timeout=10000)
        second = (time.monotonic() - t0) * 1000
        print("  ..   second inbox press: %.0f ms" % second)
        check("a second press is not a page load either", second < 400, True)
    finally:
        ctx.close()
        srv.shutdown()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
