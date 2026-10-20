"""Glass wall server: static files + loop actions. Stdlib only.

POST /api/score|propose|today -> runs bin/loop.py <cmd>, re-renders, JSON back.
POST /api/confused {"text": "..."} -> human penalty flag appended to LESSONS.md.
GET  /api/status -> current brain, scores, calls used today.
"""
import datetime as dt
import json
import subprocess
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEEDS = json.loads((ROOT / "needs.json").read_text())
SITE = Path(NEEDS["site_dir"])
SITE.mkdir(parents=True, exist_ok=True)


def run_loop(cmd):
    p = subprocess.run([str(ROOT / "bin" / "loop.py"), cmd],
                       capture_output=True, text=True, timeout=1500)
    subprocess.run([str(ROOT / "bin" / "loop.py"), "render"],
                   capture_output=True, text=True, timeout=120)
    return {"ok": p.returncode == 0, "tail": (p.stdout + p.stderr)[-1500:]}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(SITE), **kw)

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urllib.parse.urlparse(self.path).path == "/api/status":
            st = json.loads(Path(NEEDS["state_file"]).read_text()) \
                if Path(NEEDS["state_file"]).is_file() else {}
            today = dt.date.today().isoformat()
            return self._json({"current": st.get("current"),
                               "versions": {k: v.get("score")
                                            for k, v in st.get("versions", {}).items()},
                               "calls_today": st.get("calls", {}).get(today, 0),
                               "cap": NEEDS["max_calls_per_day"]})
        return super().do_GET()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        if url.path in ("/api/score", "/api/propose", "/api/today", "/api/probe"):
            try:
                return self._json(run_loop(url.path.rsplit("/", 1)[-1]))
            except subprocess.TimeoutExpired:
                return self._json({"ok": False, "tail": "timed out"}, 504)
        if url.path == "/api/confused":
            n = int(self.headers.get("Content-Length", 0) or 0)
            try:
                text = json.loads(self.rfile.read(n) or b"{}").get("text", "")
            except (json.JSONDecodeError, ValueError):
                text = ""
            text = str(text)[:300]
            if not text.strip():
                return self._json({"ok": False}, 400)
            with open(NEEDS["lessons_file"], "a") as f:
                stamp = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
                f.write(f"\n## {stamp} HUMAN FLAG (must beat AND explain better)\n"
                        f"- confusing: {text}\n")
            subprocess.run([str(ROOT / "bin" / "loop.py"), "render"],
                           capture_output=True, text=True, timeout=120)
            return self._json({"ok": True})
        return self.send_error(404)


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("0.0.0.0", int(NEEDS["port"])), Handler)
    print(f"filoeterno on 0.0.0.0:{NEEDS['port']}", flush=True)
    srv.serve_forever()
