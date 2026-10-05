#!/usr/bin/env python3
"""Phase 3 prototype API — stdlib only. Reads needs.json for port/bind/dirs."""
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NEEDS_PATH = os.path.join(ROOT, "needs.json")

with open(NEEDS_PATH) as f:
    NEEDS = json.load(f)

BIND = NEEDS.get("bind", "127.0.0.1")
PORT = int(NEEDS.get("port", 8769))
PUBLIC_DIR = os.path.join(ROOT, NEEDS.get("public_dir", "public"))
DATA_DIR = os.path.join(ROOT, "data")
TOKENS_PATH = os.path.join(DATA_DIR, "tokens.json")
PAYMENTS_PATH = os.path.join(DATA_DIR, "payments.json")

os.makedirs(DATA_DIR, exist_ok=True)
for p in (TOKENS_PATH, PAYMENTS_PATH):
    if not os.path.exists(p):
        with open(p, "w") as f:
            json.dump([], f)


def load(p):
    with open(p) as f:
        try:
            d = json.load(f)
            return d if isinstance(d, list) else []
        except (ValueError, TypeError):
            return []


def save(p, data):
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, p)


def send_json(h, code, obj):
    body = json.dumps(obj).encode()
    h.send_response(code)
    h.send_header("Content-Type", "application/json")
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)


def send_file(h, path, ctype):
    with open(path, "rb") as f:
        body = f.read()
    h.send_response(200)
    h.send_header("Content-Type", ctype)
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)


def aggregate_projects():
    tokens = load(TOKENS_PATH)
    payments = load(PAYMENTS_PATH)
    repos = {}
    for t in tokens:
        for r in (t.get("repos") or []):
            repos.setdefault(r, {"repo": r, "earned": 0.0, "due": 0.0,
                                 "refunded": 0.0, "tokens": []})
            if t.get("name") and t["name"] not in repos[r]["tokens"]:
                repos[r]["tokens"].append(t["name"])
    for p in payments:
        splits = p.get("splits") or {}
        if p.get("refunded"):
            # refunded: splits were zeroed; recover original from snapshot
            orig = p.get("splits_original") or {}
            for r, v in orig.items():
                repos.setdefault(r, {"repo": r, "earned": 0.0, "due": 0.0,
                                     "refunded": 0.0, "tokens": []})
                repos[r]["refunded"] = round(repos[r]["refunded"] + float(v), 2)
        else:
            for r, v in splits.items():
                repos.setdefault(r, {"repo": r, "earned": 0.0, "due": 0.0,
                                     "refunded": 0.0, "tokens": []})
                repos[r]["earned"] = round(repos[r]["earned"] + float(v), 2)
    for r in repos.values():
        r["due"] = r["earned"]  # prototype: everything earned is due
    return sorted(repos.values(), key=lambda x: x["repo"])


FUNDING_SAMPLE = {
    "note": "Scanner widget first (visible value); treasury use experimental. Static sample.",
    "spreads": [
        {"venue": "Drift", "market": "SOL-PERP", "funding_bps": 3.2},
        {"venue": "Zeta", "market": "SOL-PERP", "funding_bps": 1.1},
        {"venue": "Drift", "market": "JUP-PERP", "funding_bps": -2.4},
    ],
}


class Handler(BaseHTTPRequestHandler):
    server_version = "e087/1.0"

    def log_message(self, *a):
        pass

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            return json.loads(raw.decode() or "{}")
        except (ValueError, UnicodeDecodeError):
            return None

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return send_file(self, os.path.join(PUBLIC_DIR, "index.html"), "text/html; charset=utf-8")
        if path == "/refunds-note.md":
            return send_file(self, os.path.join(PUBLIC_DIR, "refunds-note.md"), "text/markdown; charset=utf-8")
        if path == "/api/health":
            return send_json(self, 200, {"ok": True, "port": PORT})
        if path == "/api/tokens":
            return send_json(self, 200, {"tokens": load(TOKENS_PATH)})
        if path == "/api/projects":
            return send_json(self, 200, {"projects": aggregate_projects()})
        if path == "/api/payments":
            return send_json(self, 200, {"payments": load(PAYMENTS_PATH)})
        if path == "/api/funding":
            return send_json(self, 200, FUNDING_SAMPLE)
        return send_json(self, 404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/tokens":
            body = self._body()
            if body is None:
                return send_json(self, 400, {"error": "invalid json"})
            name = (body.get("name") or "").strip()
            repos = body.get("repos") or []
            repos = [r.strip() for r in repos if isinstance(r, str) and r.strip()][:4]
            if not name:
                return send_json(self, 400, {"error": "name required"})
            if not repos:
                return send_json(self, 400, {"error": "at least 1 repo required"})
            tokens = load(TOKENS_PATH)
            tok = {"id": f"tok_{int(time.time()*1000)}", "name": name,
                   "repos": repos, "created_at": int(time.time())}
            tokens.append(tok)
            save(TOKENS_PATH, tokens)
            return send_json(self, 200, {"ok": True, "token": tok})
        if path == "/api/pay":
            body = self._body()
            if body is None:
                return send_json(self, 400, {"error": "invalid json"})
            method = body.get("method")
            amount = body.get("amount")
            token = (body.get("token") or "").strip()
            repos = [r for r in (body.get("repos") or []) if isinstance(r, str) and r.strip()][:4]
            if method not in ("fiat", "crypto"):
                return send_json(self, 400, {"error": "method must be fiat|crypto"})
            try:
                amount = round(float(amount), 2)
            except (TypeError, ValueError):
                return send_json(self, 400, {"error": "amount must be a number"})
            if amount <= 0:
                return send_json(self, 400, {"error": "amount must be > 0"})
            if not repos:
                return send_json(self, 400, {"error": "at least 1 repo required (revenue-share split)"})
            # auto-split equally; last repo absorbs rounding remainder
            n = len(repos)
            share = round(amount / n, 2)
            splits = {}
            acc = 0.0
            for r in repos[:-1]:
                splits[r] = share
                acc += share
            splits[repos[-1]] = round(amount - acc, 2)
            payments = load(PAYMENTS_PATH)
            stub = {"provider": "MoR stub checkout record"} if method == "fiat" \
                else {"tx": "stub-tx-placeholder"}
            pay = {"id": f"pay_{int(time.time()*1000)}", "method": method,
                   "amount": amount, "token": token, "repos": repos,
                   "splits": splits, "splits_original": dict(splits),
                   "refunded": False, "stub": stub,
                   "created_at": int(time.time())}
            payments.append(pay)
            save(PAYMENTS_PATH, payments)
            return send_json(self, 200, {"ok": True, "payment": pay})
        if path == "/api/refund":
            body = self._body()
            if body is None:
                return send_json(self, 400, {"error": "invalid json"})
            pid = body.get("payment_id") or ""
            payments = load(PAYMENTS_PATH)
            for p in payments:
                if p.get("id") == pid:
                    if p.get("refunded"):
                        return send_json(self, 200, {"ok": True, "payment": p, "note": "already refunded"})
                    # zero its splits; keep snapshot for guarantee accounting
                    p["splits_original"] = dict(p.get("splits") or {})
                    p["splits"] = {r: 0.0 for r in (p.get("repos") or [])}
                    p["refunded"] = True
                    p["refund_note"] = ("Guarantee handling: stub marks refunded, "
                                        "zeroes splits; real rails differ — see refunds-note.md.")
                    save(PAYMENTS_PATH, payments)
                    return send_json(self, 200, {"ok": True, "payment": p})
            return send_json(self, 404, {"error": "payment not found"})
        return send_json(self, 404, {"error": "not found"})


if __name__ == "__main__":
    srv = ThreadingHTTPServer((BIND, PORT), Handler)
    print(f"e087 listening on http://{BIND}:{PORT}", flush=True)
    srv.serve_forever()
