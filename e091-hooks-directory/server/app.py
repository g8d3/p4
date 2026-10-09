import json, os
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def cfg():
    with open(os.path.join(ROOT, "needs.json")) as f:
        return json.load(f)

def load(name):
    with open(os.path.join(ROOT, "data", name)) as f:
        return json.load(f)

def save(name, obj):
    with open(os.path.join(ROOT, "data", name), "w") as f:
        json.dump(obj, f, indent=1)

def usage_log(endpoint, detail, cost=0.0008):
    try:
        u = load("usage.json")
    except Exception:
        u = {"calls": []}
    import time
    u["calls"].append({"ts": int(time.time()), "endpoint": endpoint, "detail": detail, "cost": cost})
    save("usage.json", u)
    return u

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
    def serve_file(self, p, ctype="text/html"):
        with open(p, "rb") as f:
            b = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def do_POST(self):
        from urllib.parse import urlparse
        u = urlparse(self.path)
        if u.path == "/api/run":
            import time, urllib.request, urllib.parse
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                spec = load("api.json")
                eps = {e["id"]: e for e in spec["endpoints"]}
                ep_id, params = body.get("id", ""), body.get("params", {}) or {}
                custom = body.get("custom", {})
                if custom.get("path"):
                    import re
                    path = custom["path"].strip().lstrip("/")
                    if not re.fullmatch(r"[A-Za-z0-9_\-/]+", path):
                        return self.send_json({"error": "bad custom path"}, 400)
                    method = custom.get("method", "GET").upper()
                    if method not in ("GET", "POST"):
                        return self.send_json({"error": "method must be GET or POST"}, 400)
                    price, label = 0.0008, "custom:" + path
                else:
                    e = eps.get(ep_id)
                    if not e:
                        return self.send_json({"error": "unknown endpoint"}, 400)
                    path, method, price, label = e["path"].lstrip("/"), e["method"], e["price"], ep_id
                params = {k: v for k, v in params.items() if v != "" and v is not None}
                base = "https://api.twitterapis.com/twitter/" + path
                key = os.environ.get("TWITTERAPIS_API_KEY", "")
                t0 = time.time()
                if method == "GET":
                    url = base + ("?" + urllib.parse.urlencode(params) if params else "")
                    req = urllib.request.Request(url, headers={"X-API-Key": key})
                    raw = urllib.request.urlopen(req, timeout=30).read()
                else:
                    data = json.dumps(params).encode()
                    req = urllib.request.Request(base, data=data, headers={"X-API-Key": key, "Content-Type": "application/json"}, method="POST")
                    raw = urllib.request.urlopen(req, timeout=30).read()
                ms = int((time.time() - t0) * 1000)
                try:
                    payload = json.loads(raw)
                except Exception:
                    payload = {"_raw": raw[:4000].decode("utf-8", "replace")}
                usage_log("run:" + label, json.dumps(params)[:160], price)
                out = {"ok": True, "status": 200, "cost": price, "ms": ms, "data": payload}
                for ck in ("next_cursor", "cursor"):
                    if isinstance(payload, dict) and payload.get(ck):
                        out["next_cursor"] = payload[ck]
                return self.send_json(out)
            except Exception as ex:
                import urllib.error
                if isinstance(ex, urllib.error.HTTPError):
                    try:
                        err = json.loads(ex.read())
                    except Exception:
                        err = {"error": "http_" + str(ex.code)}
                    usage_log("run-failed", str(body)[:120], 0.0)
                    return self.send_json({"ok": False, "status": ex.code, "cost": 0.0, "data": err})
                return self.send_json({"ok": False, "error": str(ex)[:200]})
        if u.path == "/api/save":
            import re, subprocess
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                label = re.sub(r"[^a-z0-9-]+", "-", str(body.get("label", "adhoc")).lower()).strip("-")[:40] or "adhoc"
                data = body.get("data")
                if not isinstance(data, dict):
                    return self.send_json({"error": "no result data"}, 400)
                fn = os.path.join(ROOT, "evidence", label + ".json")
                data.setdefault("captured", __import__("datetime").date.today().isoformat())
                if os.path.exists(fn) and isinstance(data.get("tweets"), list):
                    try:
                        prev = json.load(open(fn))
                        seen = set(t.get("id") for t in data["tweets"])
                        for t in prev.get("tweets", []):
                            if t.get("id") not in seen:
                                data["tweets"].append(t)
                                seen.add(t.get("id"))
                    except Exception:
                        pass
                json.dump(data, open(fn, "w"), indent=1)
                subprocess.run(["python3", os.path.join(ROOT, "bin", "import_evidence.py")], capture_output=True, timeout=60)
                usage_log("save-evidence", label, 0.0)
                return self.send_json({"ok": True, "file": os.path.basename(fn),
                                        "tweets": len(data.get("tweets", []))})
            except Exception as ex:
                return self.send_json({"error": str(ex)[:200]})
        if u.path == "/api/settings":
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                c = cfg()
                if "credits_balance" in body:
                    v = body["credits_balance"]
                    c["credits_balance"] = None if v is None else round(float(v), 4)
                    with open(os.path.join(ROOT, "needs.json"), "w") as f:
                        json.dump(c, f, indent=1)
                return self.send_json({"ok": True, "credits_balance": c.get("credits_balance")})
            except Exception as e:
                return self.send_json({"error": str(e)[:120]}, 400)
        return self.send_json({"error": "not found"}, 404)
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/health":
            c = cfg()
            return self.send_json({"ok": True, "port": c["port"]})
        if u.path == "/api/hooks":
            return self.send_json({"hooks": load("hooks.json"), "updated": "2026-10-09", "source": "twitterapis.com"})
        if u.path == "/api/evidence":
            return self.send_json(load("evidence.json"))
        if u.path == "/api/sources":
            return self.send_json(load("sources.json"))
        if u.path == "/api/signals":
            return self.send_json(load("signals.json"))
        if u.path == "/api/pairs":
            return self.send_json(load("pairs.json"))
        if u.path == "/api/spec":
            return self.send_json(load("api.json"))
        if u.path == "/api/files":
            import sqlite3
            try:
                con = sqlite3.connect(os.path.join(ROOT, "data", "evidence.db"))
                files = [{"file": r[0], "query": r[1], "tweets": r[2]}
                         for r in con.execute("SELECT file, query, COUNT(*) FROM tweets GROUP BY file, query ORDER BY file")]
                con.close()
            except Exception:
                files = []
            return self.send_json({"files": files})
        if u.path == "/api/usage":
            try:
                u2 = load("usage.json")
            except Exception:
                u2 = {"calls": []}
            spent = round(sum(c.get("cost", 0) for c in u2["calls"]), 4)
            bal = cfg().get("credits_balance")
            return self.send_json({"calls": len(u2["calls"]), "spent_usd": spent,
                                    "price_per_read": 0.0008, "balance_usd": bal,
                                    "log": u2["calls"][-25:]})
        if u.path == "/api/tweet":
            import sqlite3
            from urllib.parse import parse_qs
            tid = (parse_qs(u.query).get("id") or [""])[0]
            try:
                con = sqlite3.connect(os.path.join(ROOT, "data", "evidence.db"))
                con.row_factory = sqlite3.Row
                r = con.execute("SELECT * FROM tweets WHERE id=?", (tid,)).fetchone()
                con.close()
            except Exception:
                r = None
            if r is None:
                return self.send_json({"error": "not in captured evidence"}, 404)
            cols = list(r.keys())
            t = json.loads(r["raw"]) if r["raw"] else {}
            return self.send_json({
                "file": r["file"], "query": r["query"], "queryType": r["query_type"],
                "count": r["count"], "captured": r["captured"],
                "index": r["idx"], "page": (r["idx"] or 0) // 20 + 1, "page_size": 20,
                "tweet": t, "stored_cols": cols})
        if u.path == "/api/tweets.csv":
            import csv, io, sqlite3
            try:
                con = sqlite3.connect(os.path.join(ROOT, "data", "evidence.db"))
                rows = con.execute("SELECT id,query,date,time_utc,author,author_followers,likes,reposts,replies,quotes,bookmarks,views,lang,url,text FROM tweets ORDER BY date DESC,time_utc DESC").fetchall()
                con.close()
            except Exception:
                rows = []
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["id", "query", "date", "time_utc", "author", "author_followers", "likes", "reposts", "replies", "quotes", "bookmarks", "views", "lang", "url", "text"])
            w.writerows(rows)
            b = buf.getvalue().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Disposition", 'attachment; filename="e091-tweets.csv"')
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            return self.wfile.write(b)
        if u.path == "/api/credits":
            import time, urllib.request
            now = int(time.time())
            try:
                st = load("rl_state.json")
            except Exception:
                st = {}
            if now - st.get("ts", 0) < 60 and "remaining" in st:
                return self.send_json(st)
            key = os.environ.get("TWITTERAPIS_API_KEY", "")
            req = urllib.request.Request(
                "https://api.twitterapis.com/twitter/user/info?userName=Hookrfun",
                headers={"X-API-Key": key})
            try:
                r = urllib.request.urlopen(req, timeout=15)
                hd = dict(r.headers.items())
                usage_log("user/info (rate probe)", "credits widget refresh", 0.0008)
                st = {"ts": now,
                      "limit": hd.get("x-ratelimit-limit"),
                      "remaining": hd.get("x-ratelimit-remaining"),
                      "reset": hd.get("x-ratelimit-reset"),
                      "note": "probe costs $0.0008; cached 60s"}
                save("rl_state.json", st)
                return self.send_json(st)
            except Exception as e:
                return self.send_json({"error": str(e)[:120]}, 502)
        if u.path in ("/", "/index.html"):
            return self.serve_file(os.path.join(ROOT, "public", "index.html"))
        return self.send_json({"error": "not found"}, 404)

if __name__ == "__main__":
    c = cfg()
    srv = ThreadingHTTPServer((c["bind"], c["port"]), H)
    print(f"e091 serving on {c['port']}")
    srv.serve_forever()
