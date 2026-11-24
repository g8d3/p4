"""A backlog drains in batches, not in one request the inbox refuses.

The phone that came back from the x-web outage had 499 captures waiting; the
client posted all of them as one 600 KB request, got 413 ("payload too large"),
and every later capture queued behind a backlog that could never leave. This
drives the real background against a local inbox that records the body size of
each POST: the queue must go out in several bounded requests, every uid once,
and the outbox must end empty.

    xvfb-run -a python3 tests/review_backlog.py
"""
import http.server
import json
import pathlib
import socket
import sys
import tempfile
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
EXT = str((ROOT.parent / "extension").resolve())
APPID = "jmfddigdennhnndgaecgppajnjabhlgm"
N = 499
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


class Sink(http.server.BaseHTTPRequestHandler):
    posts = []
    uids = []
    done = threading.Event()

    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/likes"):
            self._send(200, {"ok": True, "items": [], "total": 0, "user": "u_test", "phones": 1})
        else:
            self._send(200, {"ok": True, "api": 4})

    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(n)
        if self.path.startswith("/api/telemetry"):
            return self._send(200, {"ok": True, "stored": 0})
        if self.path.startswith("/api/claim"):
            return self._send(200, {"ok": True, "token": "a" * 32, "user": "u_test"})
        try:
            items = json.loads(raw or b"{}").get("items", [])
        except Exception:
            return self._send(400, {"ok": False, "error": "bad json"})
        Sink.posts.append(n)
        Sink.uids.extend(it.get("uid") for it in items)
        if len(set(Sink.uids)) >= N:
            Sink.done.set()
        self._send(200, {"ok": True, "received": len(items), "used": len(set(Sink.uids)), "quota": 3000, "user": "u_test"})


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Sink)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        tempfile.mkdtemp(prefix="echolike-backlog-"),
        headless=False,
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-sandbox"],
    )
    page = ctx.new_page()
    page.goto(f"chrome-extension://{APPID}/app.html")
    page.wait_for_timeout(800)
    made = page.evaluate(
        """async ([n, url]) => {
          const b64 = (u8) => btoa(String.fromCharCode.apply(null, Array.from(u8)))
            .replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=+$/, '');
          const unb64 = (s) => {
            let t = s.replace(/-/g, '+').replace(/_/g, '/');
            while (t.length % 4) t += '=';
            const b = atob(t); const u = new Uint8Array(b.length);
            for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i);
            return u;
          };
          const s = await chrome.storage.local.get({ key: '' });
          const k = await crypto.subtle.importKey('raw', unb64(s.key), 'AES-GCM', false, ['encrypt']);
          const items = [], outbox = [];
          for (let i = 0; i < n; i++) {
            const it = { uid: 'bk-' + i, kind: 'like', id: String(1000000 + i), handle: 'tester',
              url: 'https://x.com/tester/status/' + (1000000 + i), text: 'backlog item ' + i,
              clicked_at: new Date().toISOString() };
            items.push(it);
            const iv = crypto.getRandomValues(new Uint8Array(12));
            const ct = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, k, new TextEncoder().encode(JSON.stringify(it)));
            outbox.push({ uid: it.uid, iv: b64(iv), ct: b64(new Uint8Array(ct)) });
          }
          await chrome.storage.local.set({ url, token: 'a'.repeat(32), key: s.key, items, outbox, last: null, defaultTriedAt: Date.now() });
          return outbox.length;
        }""",
        [N, f"http://127.0.0.1:{port}"],
    )
    check("the backlog was staged", made, N)

    page.evaluate("() => chrome.runtime.sendMessage({ type: 'retry' })")
    drained = Sink.done.wait(90)
    check("every capture reached the inbox", drained, True)
    check("all uids delivered once", len(Sink.uids), len(set(Sink.uids)))
    check("the queue went out in more than one request", len(Sink.posts) > 1, True)
    check("no request is over the client budget", max(Sink.posts or [0]) <= 300 * 1024, True)
    print("  info requests: " + ", ".join(str(x) for x in Sink.posts[:8]))

    page.wait_for_timeout(500)
    left = page.evaluate("async () => (await chrome.storage.local.get({ outbox: [] })).outbox.length")
    check("the outbox ended empty", left, 0)
    ctx.close()

srv.shutdown()
print()
if failures:
    print("FAILED: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
