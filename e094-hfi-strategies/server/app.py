"""e094 server: stdlib only. Serves public/ + /api/health + /api/needs."""
import json, os, threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "needs.json")) as f:
    NEEDS = json.load(f)

PUBLIC = os.path.join(ROOT, NEEDS.get("public_dir", "public"))

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=PUBLIC, **kw)
    def log_message(self, *a):
        pass
    def do_GET(self):
        if self.path == "/api/health":
            body = json.dumps({"ok": True, "experiment": "e094-hfi-strategies"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/needs":
            body = json.dumps(NEEDS).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

if __name__ == "__main__":
    srv = ThreadingHTTPServer((NEEDS.get("host", "127.0.0.1"), NEEDS["port"]), H)
    print(f"e094 on http://{NEEDS.get('host','127.0.0.1')}:{NEEDS['port']}/", flush=True)
    srv.serve_forever()
