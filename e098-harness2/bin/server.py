"""Static file server for the e098 results site + POST /api/rerun action. Stdlib only."""

import json
import subprocess
import urllib.parse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEEDS = json.loads((ROOT / "needs.json").read_text())
SITE = Path(NEEDS["site_dir"])
SITE.mkdir(parents=True, exist_ok=True)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(SITE), **kw)

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        if url.path != "/api/rerun":
            return self.send_error(404)
        q = urllib.parse.parse_qs(url.query)
        try:
            k = int(q.get("k", ["2"])[0])
            k = min(max(k, 1), 4)
        except ValueError:
            return self.send_error(400, "k must be an integer")
        try:
            p = subprocess.run(
                [str(ROOT / "bin" / "demo.sh"), str(k)],
                capture_output=True, text=True, timeout=300,
            )
        except subprocess.TimeoutExpired:
            return self.send_error(504, "demo timed out")
        ok = p.returncode == 0
        body = json.dumps({
            "ok": ok, "k": k,
            "tail": (p.stdout + p.stderr)[-2000:],
        }).encode()
        self.send_response(200 if ok else 500)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("0.0.0.0", int(NEEDS["port"])), Handler)
    print(f"e098 serving {SITE} on 127.0.0.1:{NEEDS['port']}", flush=True)
    srv.serve_forever()
