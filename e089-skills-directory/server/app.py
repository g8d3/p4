import json, os, re, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def cfg():
    with open(os.path.join(ROOT, "needs.json")) as f:
        return json.load(f)

def skills():
    with open(os.path.join(ROOT, "data", "skills.json")) as f:
        return json.load(f)

def indexers():
    with open(os.path.join(ROOT, "data", "indexers.json")) as f:
        return json.load(f)

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def send_json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def serve_file(self, p):
        with open(p, "rb") as f:
            b = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        return self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/health":
            return self.send_json({"ok": True, "ts": int(time.time())})
        if u.path == "/api/skills":
            return self.send_json({"skills": skills(), "updated": "2026-10-05"})
        if u.path == "/api/indexers":
            return self.send_json({"indexers": indexers(), "updated": "2026-10-08"})
        if u.path in ("/mobile", "/mobile.html"):
            return self.serve_file(os.path.join(ROOT, "public", "mobile.html"))
        if u.path in ("/m1", "/m2", "/m3", "/m4", "/m5"):
            return self.serve_file(os.path.join(ROOT, "public", u.path[1:] + ".html"))
        if u.path in ("/", "/index.html"):
            p = os.path.join(ROOT, "public", "index.html")
            return self.serve_file(p)
        if u.path in ("/v2", "/v2.html"):
            p = os.path.join(ROOT, "public", "v2.html")
            return self.serve_file(p)
        if u.path in ("/versions", "/versions.html"):
            return self.serve_file(os.path.join(ROOT, "public", "versions.html"))
        m = re.fullmatch(r"/(v(?:[2-9]|1[0-3]))(\.html)?", u.path)
        if m:
            return self.serve_file(os.path.join(ROOT, "public", m.group(1) + ".html"))
        self.send_response(404)
        self.end_headers()

def main():
    c = cfg()
    srv = ThreadingHTTPServer((c["bind"], c["port"]), H)
    print(f"e089 on {c['bind']}:{c['port']}", flush=True)
    srv.serve_forever()

if __name__ == "__main__":
    main()
