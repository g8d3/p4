#!/usr/bin/env python3
"""BookmarkVault backend stub (v0.1.0) — in-memory endpoints, test-mode webhooks.

Run:
  python3 backend/server.py            # serves on :8899
  python3 backend/server.py --port 8899

Auth: Bearer user token. Any non-empty token is accepted in stub mode
  (single demo user "demo"). Missing/empty token -> 401, except open
  routes: /health, /v1/referrals/attribute, billing webhooks.

Spec: ag-01/SPEC.md section 2. Webhook handlers run in TEST MODE until
  a human wires production keys via ops/cycle.html (Keys tab):
  - If the relevant secret env var is present, a signature is checked.
  - Else the event is logged as `unverified-test-event` and only
    `plan: test` is ever entitled (never a paid plan).
Secrets (env, never committed):
  FIAT_WEBHOOK_SECRET, CRYPTO_WEBHOOK_SECRET, BV_API_TOKEN (optional pin)

Data is IN-MEMORY only (process restart wipes it). Webhook events are
also appended to backend/webhook-log.jsonl for inspection.
"""
import hashlib
import hmac
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

VERSION = "v0.1.0"
HERE = os.path.dirname(os.path.abspath(__file__))
WEBHOOK_LOG = os.path.join(HERE, "webhook-log.jsonl")

# --- price plans (must match sites/landing/pricing.html + terms.html) ---
PLANS = {
    "free":     {"id": "free",     "price_usd": 0,   "interval": "none",
                   "label": "Free"},
    "monthly":  {"id": "monthly",  "price_usd": 7,   "interval": "month",
                   "label": "Monthly $7/mo"},
    "yearly":   {"id": "yearly",   "price_usd": 99,  "interval": "year",
                   "label": "Yearly $99/yr"},
    "lifetime": {"id": "lifetime", "price_usd": 198, "interval": "once",
                   "label": "Lifetime $198 one-time"},
    "test":     {"id": "test",     "price_usd": 0,   "interval": "none",
                   "label": "Test (no keys wired)"},
}
# legacy alias: early stub entitled generic "pro" — treat as monthly.
PLAN_ALIASES = {"pro": "monthly", "reader": "monthly", "annual": "yearly"}


def resolve_plan(body):
    """Map a webhook payload to a plan id. Accepts plan/price_id/interval.
    Unknown or missing -> monthly (landing default paid plan)."""
    if not isinstance(body, dict):
        return "monthly"
    for key in ("plan", "price_id", "price", "interval", "tier"):
        raw = str(body.get(key, "") or "").strip().lower()
        if not raw:
            continue
        if raw in PLANS:
            return raw
        if raw in PLAN_ALIASES:
            return PLAN_ALIASES[raw]
        # price-id style: bv-monthly, price_yearly_..., lifetime-usd...
        for pid in ("lifetime", "yearly", "monthly"):
            if pid in raw:
                return pid
        if raw in ("month", "monthly-usd-7", "$7"):
            return "monthly"
        if raw in ("year", "$99"):
            return "yearly"
        if raw in ("once", "one-time", "$198"):
            return "lifetime"
    return "monthly"

# --- in-memory store (single demo user; per-token namespace skipped for stub) ---
STORE = {
    "tweets": {},        # id -> {id,text,author,created_at,source,labels:[],imported_at}
    "labels": {},        # name -> {name, created_at}
    "outbound_webhooks": [],  # [{url, events, created_at}]
    "approvals": [],       # [{id,kind,title,detail,status,created_at,decided_at,reason}]
    "approval_seq": 0,
    "referral": {"code": "DEMO42", "clicks": 0, "held": 0, "payable": 0, "currency": "USD",
                 "attributions": [], "log": []},
    "entitlements": {"plan": "free", "updated_at": None, "history": []},
    "events": [],        # test-mode webhook receipts
}

OPEN_PATHS = ("/health", "/v1/referrals/attribute",
              "/v1/billing/fiat-webhook", "/v1/billing/crypto-webhook")


def log_event(obj):
    STORE["events"].append(obj)
    try:
        with open(WEBHOOK_LOG, "a") as f:
            f.write(json.dumps(obj) + "\n")
    except Exception:
        pass


def send_json(h, code, obj, extra_headers=None):
    body = json.dumps(obj).encode()
    h.send_response(code)
    h.send_header("Content-Type", "application/json")
    h.send_header("Content-Length", str(len(body)))
    h.send_header("Access-Control-Allow-Origin", "*")
    h.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
    h.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
    for k, v in (extra_headers or {}).items():
        h.send_header(k, v)
    h.end_headers()
    h.wfile.write(body)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
        except Exception:
            n = 0
        raw = self.rfile.read(n) if n else b""
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {"_raw": raw.decode("utf-8", "replace")}

    def _authed(self, path):
        if path in OPEN_PATHS or path == "/":
            return True
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or len(auth) < 9:
            return False
        pin = os.environ.get("BV_API_TOKEN", "")
        if pin and auth != "Bearer " + pin:
            return False
        return True

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        path, qs = u.path, parse_qs(u.query)
        if path in ("/", "/health"):
            return send_json(self, 200, {"ok": True, "service": "bookmarkvault-stub",
                                         "version": VERSION, "mode": "test"})
        if not self._authed(path):
            return send_json(self, 401, {"ok": False, "error": "missing-bearer-token",
                                         "hint": "Set bv.token in extension sidepanel Settings."})
        if path == "/v1/bookmarks":
            q = (qs.get("q", [""])[0] or "").lower()
            label = qs.get("label", [""])[0]
            out = list(STORE["tweets"].values())
            if label:
                out = [t for t in out if label in t.get("labels", [])]
            if q:
                out = [t for t in out if q in (t.get("text", "") + " " + t.get("author", "")).lower()]
            out.sort(key=lambda t: t.get("created_at", ""), reverse=True)
            return send_json(self, 200, {"tweets": out[:100], "total": len(out)})
        if path == "/v1/labels":
            return send_json(self, 200, {"labels": sorted(STORE["labels"].values(),
                                                          key=lambda l: l["name"])})
        if path == "/v1/webhooks/bookmarks":
            return send_json(self, 200, {"webhooks": STORE["outbound_webhooks"]})
        if path == "/v1/approvals":
            status = (qs.get("status", [""])[0] or "").strip().lower()
            items = list(STORE["approvals"])
            if status:
                items = [a for a in items if a.get("status") == status]
            items.sort(key=lambda a: a.get("created_at", ""), reverse=True)
            return send_json(self, 200, {"approvals": items[:100],
                                         "total": len(items)})
        if path == "/v1/referrals/me":
            r = STORE["referral"]
            return send_json(self, 200, {"code": r["code"], "clicks": r["clicks"],
                                         "held": r["held"], "payable": r["payable"],
                                         "currency": r["currency"]})
        if path == "/v1/billing/me":
            e = STORE["entitlements"]
            plan = PLANS.get(e.get("plan", "free"), PLANS["free"])
            return send_json(self, 200, {"plan": e.get("plan", "free"),
                                         "plan_detail": plan,
                                         "updated_at": e.get("updated_at"),
                                         "history": e.get("history", []),
                                         "catalog": [PLANS[k] for k in
                                                       ("free", "monthly", "yearly", "lifetime")],
                                         "mode": "test" if e.get("plan") in ("free", "test") else "live"})
        return send_json(self, 404, {"ok": False, "error": "not-found", "path": path})

    def do_POST(self):
        u = urlparse(self.path)
        path = u.path
        body = self._body()
        if path not in OPEN_PATHS and not self._authed(path):
            return send_json(self, 401, {"ok": False, "error": "missing-bearer-token"})
        now = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

        if path == "/v1/bookmarks/import":
            tweets = body.get("tweets", []) if isinstance(body, dict) else []
            accepted, dupes = 0, 0
            for t in tweets[:500]:
                tid = str(t.get("id", "") or "")
                if not tid:
                    continue
                if tid in STORE["tweets"]:
                    dupes += 1
                    # XHR wins on conflict (extension merge rule): refresh text if new source is xhr
                    if t.get("source") == "xhr":
                        STORE["tweets"][tid].update({k: t[k] for k in
                                                     ("text", "author", "created_at", "source")
                                                     if k in t})
                    continue
                STORE["tweets"][tid] = {
                    "id": tid, "text": t.get("text", "")[:2000],
                    "author": t.get("author", "")[:120],
                    "created_at": t.get("created_at", ""),
                    "source": t.get("source", "dom") if t.get("source") in ("xhr", "dom") else "dom",
                    "labels": [], "imported_at": now}
                accepted += 1
            # fire outbound webhooks (best-effort log; no network in stub)
            for wh in STORE["outbound_webhooks"]:
                log_event({"type": "outbound-bookmark-event", "to": wh["url"],
                           "accepted": accepted, "at": now})
            return send_json(self, 200, {"accepted": accepted, "dupes": dupes,
                                         "total": len(STORE["tweets"])})

        if path == "/v1/labels":
            name = str(body.get("name", "") or "").strip()[:40]
            if not name:
                return send_json(self, 400, {"ok": False, "error": "name-required"})
            STORE["labels"].setdefault(name, {"name": name, "created_at": now})
            return send_json(self, 200, {"ok": True, "label": STORE["labels"][name]})

        if path.startswith("/v1/bookmarks/") and path.endswith("/labels"):
            tid = path[len("/v1/bookmarks/"):-len("/labels")]
            tw = STORE["tweets"].get(tid)
            if not tw:
                return send_json(self, 404, {"ok": False, "error": "tweet-not-found"})
            name = str(body.get("label", body.get("name", "")) or "").strip()[:40]
            if not name:
                return send_json(self, 400, {"ok": False, "error": "label-required"})
            STORE["labels"].setdefault(name, {"name": name, "created_at": now})
            if name not in tw["labels"]:
                tw["labels"].append(name)
            return send_json(self, 200, {"ok": True, "id": tid, "labels": tw["labels"]})

        if path == "/v1/webhooks/bookmarks":
            url = str(body.get("url", "") or "")[:500]
            if not (url.startswith("https://") or url.startswith("http://localhost")):
                return send_json(self, 400, {"ok": False,
                                             "error": "https-url-required"})
            if url not in [w["url"] for w in STORE["outbound_webhooks"]]:
                STORE["outbound_webhooks"].append({"url": url, "events": ["bookmarks.imported"],
                                                   "created_at": now})
            return send_json(self, 200, {"ok": True, "webhooks": STORE["outbound_webhooks"]})

        if path == "/v1/approvals":
            kind = str(body.get("kind", "") or "").strip()[:40] or "general"
            title = str(body.get("title", "") or "").strip()[:120]
            if not title:
                return send_json(self, 400, {"ok": False,
                                             "error": "title-required"})
            STORE["approval_seq"] += 1
            item = {"id": STORE["approval_seq"], "kind": kind,
                    "title": title,
                    "detail": str(body.get("detail", "") or "")[:500],
                    "status": "pending", "created_at": now,
                    "decided_at": None, "reason": ""}
            STORE["approvals"].append(item)
            return send_json(self, 200, {"ok": True, "approval": item})

        if path.startswith("/v1/approvals/") and \
                (path.endswith("/approve") or path.endswith("/reject")):
            decide = "approved" if path.endswith("/approve") else "rejected"
            try:
                aid = int(path[len("/v1/approvals/"):].split("/")[0])
            except Exception:
                return send_json(self, 404, {"ok": False,
                                             "error": "approval-not-found"})
            item = next((a for a in STORE["approvals"]
                         if a.get("id") == aid), None)
            if not item:
                return send_json(self, 404, {"ok": False,
                                             "error": "approval-not-found"})
            if item["status"] != "pending":
                return send_json(self, 200, {"ok": True, "approval": item,
                                             "note": "already-decided"})
            item["status"] = decide
            item["decided_at"] = now
            item["reason"] = str(body.get("reason", "") or "")[:200]
            return send_json(self, 200, {"ok": True, "approval": item})

        if path == "/v1/referrals/attribute":
            code = str(body.get("code", "") or "").strip().upper()[:16]
            r = STORE["referral"]
            if code == r["code"]:
                r["log"].append({"at": now, "reason": "self-referral"})
                return send_json(self, 200, {"attributed": False, "reason": "self-referral"})
            if not code or len(code) < 4:
                return send_json(self, 200, {"attributed": False, "reason": "bad-code"})
            r["clicks"] += 1
            r["attributions"].append({"code": code, "at": now})
            return send_json(self, 200, {"attributed": True, "code": code},
                             {"Set-Cookie": f"bv_ref={code}; Max-Age=2592000; Path=/; SameSite=Lax"})

        if path == "/v1/billing/fiat-webhook":
            secret = os.environ.get("FIAT_WEBHOOK_SECRET", "")
            sig = self.headers.get("X-Webhook-Signature", "")
            etype = str(body.get("type", "") or "")
            if secret:
                expect = hmac.new(secret.encode(), json.dumps(body).encode(),
                                  hashlib.sha256).hexdigest()
                if not hmac.compare_digest(expect, sig):
                    log_event({"type": "fiat-webhook", "status": "bad-signature", "at": now})
                    return send_json(self, 401, {"ok": False, "error": "bad-signature"})
                if etype == "checkout.completed":
                    plan = resolve_plan(body)
                    STORE["entitlements"] = {"plan": plan, "updated_at": now,
                                             "history": STORE["entitlements"]["history"] +
                                             [{"at": now, "via": "fiat", "event": etype,
                                               "plan": plan}]}
                    return send_json(self, 200, {"ok": True, "plan": plan,
                                                 "plan_detail": PLANS[plan]})
                return send_json(self, 200, {"ok": True, "ignored": etype})
            # TEST MODE: never entitle paid plans
            log_event({"type": "fiat-webhook", "status": "unverified-test-event",
                       "event": etype, "at": now})
            STORE["entitlements"]["history"].append({"at": now, "via": "fiat-test",
                                                     "event": etype or "test"})
            return send_json(self, 200, {"ok": True, "plan": "test", "mode": "test",
                                         "note": "unverified-test-event; wire FIAT_WEBHOOK_SECRET via ops/cycle.html (Keys tab)"})

        if path == "/v1/billing/crypto-webhook":
            secret = os.environ.get("CRYPTO_WEBHOOK_SECRET", "")
            sig = self.headers.get("X-Webhook-Signature", "")
            status = str(body.get("status", "") or "")
            if secret:
                expect = hmac.new(secret.encode(), json.dumps(body).encode(),
                                  hashlib.sha256).hexdigest()
                if not hmac.compare_digest(expect, sig):
                    log_event({"type": "crypto-webhook", "status": "bad-signature", "at": now})
                    return send_json(self, 401, {"ok": False, "error": "bad-signature"})
                if status == "confirmed":
                    plan = resolve_plan(body)
                    STORE["entitlements"] = {"plan": plan, "updated_at": now,
                                             "history": STORE["entitlements"]["history"] +
                                             [{"at": now, "via": "crypto", "event": status,
                                               "plan": plan}]}
                    return send_json(self, 200, {"ok": True, "plan": plan,
                                                 "plan_detail": PLANS[plan]})
                return send_json(self, 200, {"ok": True, "ignored": status})
            log_event({"type": "crypto-webhook", "status": "unverified-test-event",
                       "event": status, "at": now})
            STORE["entitlements"]["history"].append({"at": now, "via": "crypto-test",
                                                     "event": status or "test"})
            return send_json(self, 200, {"ok": True, "plan": "test", "mode": "test",
                                         "note": "unverified-test-event; wire CRYPTO_WEBHOOK_SECRET via ops/cycle.html (Keys tab)"})

        return send_json(self, 404, {"ok": False, "error": "not-found", "path": path})

    def do_DELETE(self):
        u = urlparse(self.path)
        path = u.path
        if not self._authed(path):
            return send_json(self, 401, {"ok": False, "error": "missing-bearer-token"})
        if path.startswith("/v1/bookmarks/") and path.endswith("/labels"):
            tid = path[len("/v1/bookmarks/"):-len("/labels")]
            tw = STORE["tweets"].get(tid)
            if not tw:
                return send_json(self, 404, {"ok": False, "error": "tweet-not-found"})
            body = self._body()
            # label may come in body or ?label=
            q = parse_qs(u.query)
            name = str(body.get("label", body.get("name", q.get("label", [""])[0])) or "")
            tw["labels"] = [l for l in tw.get("labels", []) if l != name]
            return send_json(self, 200, {"ok": True, "id": tid, "labels": tw["labels"]})
        return send_json(self, 404, {"ok": False, "error": "not-found"})


if __name__ == "__main__":
    port = 8899
    for i, a in enumerate(sys.argv):
        if a == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
    print(f"BookmarkVault backend stub {VERSION} on :{port} (test mode, in-memory)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
