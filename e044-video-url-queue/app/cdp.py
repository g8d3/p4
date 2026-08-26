import json
import shutil
import socket
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

import websocket

COLLECT_JS = """
(() => {
  const out = [];
  const push = (s) => { if (s && !out.includes(s)) out.push(s); };
  document.querySelectorAll('video').forEach(v => {
    push(v.currentSrc || v.src || (v.querySelector('source') || {}).src);
    (v.querySelectorAll('source') || []).forEach(s => push(s.src));
  });
  document.querySelectorAll('a[href]').forEach(a => {
    const h = a.getAttribute('href') || '';
    if (/\\.(mp4|webm|m3u8|mov|mkv)(\\?|$)/i.test(h)) push(h);
  });
  return JSON.stringify(out);
})()
"""


def find_chrome() -> str | None:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        p = shutil.which(name)
        if p:
            return p
    return None


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Browser:
    def __init__(self, data_dir: Path, log=None):
        self.data_dir = data_dir
        self.log = log or (lambda *a: None)
        self.proc = None
        self.port = None
        self.chrome = find_chrome()

    def ensure(self) -> bool:
        if self.proc and self.proc.poll() is None:
            return True
        if not self.chrome:
            return False
        self.port = _free_port()
        profile = self.data_dir / "chrome-profile"
        profile.mkdir(parents=True, exist_ok=True)
        for stale in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
            (profile / stale).unlink(missing_ok=True)
        self.proc = subprocess.Popen(
            [
                self.chrome, "--headless=new", f"--remote-debugging-port={self.port}",
                f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
                "--mute-audio", "--disable-dev-shm-usage", "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(20):
            if self.proc.poll() is not None:
                return False
            if self._http(f"/json/version") is not None:
                return True
            time.sleep(0.5)
        return False

    def _http(self, path: str, method: str = "GET") -> dict | None:
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{self.port}{path}", method=method
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return None

    def collect_videos(self, url: str, timeout_s: int = 30) -> list[str]:
        if not self.ensure():
            raise RuntimeError("no browser binary found (google-chrome/chromium)")
        target = self._http(f"/json/new?{urllib.parse.quote(url, safe='')}", method="PUT")
        if not target:
            raise RuntimeError("could not open browser tab")
        try:
            ws = websocket.create_connection(
                target["webSocketDebuggerUrl"], timeout=timeout_s
            )
            return self._collect(ws, url, timeout_s)
        finally:
            try:
                ws.close()
            except Exception:
                pass
            self._http(f"/json/close/{target['id']}", method="GET")

    def _collect(self, ws, url: str, timeout_s: int) -> list[str]:
        mid = 0

        def send(method, params=None):
            nonlocal mid
            mid += 1
            ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
            return mid

        def wait_response(msg_id, timeout=8.0):
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    ws.settimeout(0.5)
                    msg = json.loads(ws.recv())
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception:
                    break
                if msg.get("id") == msg_id:
                    return msg
            return {}

        def eval_expr(expr):
            msg_id = send("Runtime.evaluate", {
                "expression": expr,
                "returnByValue": True,
            })
            msg = wait_response(msg_id)
            return ((msg.get("result") or {}).get("result") or {}).get("value")

        send("Page.enable")
        wait_response(send("Page.navigate", {"url": url}))

        deadline = time.time() + timeout_s
        count = -1
        stable = 0
        complete_since = None
        while time.time() < deadline:
            raw = eval_expr(
                "document.readyState + '|' + document.querySelectorAll('video').length"
            )
            parts = str(raw or "loading|0").split("|", 1)
            ready = parts[0]
            try:
                n = int(parts[1])
            except ValueError:
                n = 0
            if n == count:
                stable += 1
            else:
                count, stable = n, 0
            if ready == "complete":
                complete_since = complete_since or time.time()
                if n > 0 and stable >= 4:
                    break
                if time.time() - complete_since > 15:
                    break
            time.sleep(1.0)

        value = eval_expr(COLLECT_JS)
        if not value:
            time.sleep(2.0)
            value = eval_expr(COLLECT_JS)
        if value and isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return [value]
        raise RuntimeError("browser did not return video list")
