#!/usr/bin/env python3
"""BeanBadge demo server — stdlib only. Bind 127.0.0.1:8337.

Env wiring (strict, no mocks):
  STRIPE_SECRET_KEY      -> real Stripe Checkout sessions via api.stripe.com
  CLERK_PUBLISHABLE_KEY  -> served to the frontend so real Clerk JS can load
  RESEND_API_KEY         -> real sends via api.resend.com
  FROM_EMAIL             -> sender identity for Resend (default onboarding@resend.dev)
  BEANBADGE_DOMAIN       -> domain pick label (default beanbadge.coffee, check-only)
With a key unset the matching feature returns an honest 400/disabled state.
"""
import base64
import json
import os
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
INDEX = HERE / "index.html"
PORT = int(os.environ.get("BEANBADGE_PORT", "8337"))
HOST = "127.0.0.1"
DOMAIN = os.environ.get("BEANBADGE_DOMAIN", "beanbadge.coffee")
PLANS = {"taster": ("Taster — 1 bag/mo", 1200), "daily": ("Daily Drinker — 2 bags/mo", 1900), "office": ("Office Fuel — 6 bags/mo", 4900)}


def cfg():
    return {
        "stripe_ready": bool(os.environ.get("STRIPE_SECRET_KEY")),
        "clerk_ready": bool(os.environ.get("CLERK_PUBLISHABLE_KEY")),
        "clerk_publishable_key": os.environ.get("CLERK_PUBLISHABLE_KEY", "") if os.environ.get("CLERK_PUBLISHABLE_KEY") else "",
        "resend_ready": bool(os.environ.get("RESEND_API_KEY")),
        "domain": DOMAIN,
        "domain_note": "RDAP check-only via swarm-market /api/domain-check (likely free, NOT purchased). Confirm + buy at registrar before launch.",
    }


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        try:
            return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0) or 0)) or b"{}")
        except Exception:
            return {}

    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        if p in ("/", "/index.html"):
            b = INDEX.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif p == "/api/config":
            self._json(cfg())
        elif p == "/api/health":
            self._json({"ok": True, "service": "beanbadge-demo", **cfg()})
        else:
            self.send_error(404)

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        body = self._body()
        if p == "/api/checkout":
            key = os.environ.get("STRIPE_SECRET_KEY", "")
            if not key:
                return self._json({"error": "payments unconnected: STRIPE_SECRET_KEY is not set. No mock charge offered."}, 400)
            plan = body.get("plan", "daily")
            name, cents = PLANS.get(plan, PLANS["daily"])
            host = self.headers.get("Host", f"{HOST}:{PORT}")
            data = {
                "mode": "subscription",
                "success_url": f"http://{host}/?paid=1",
                "cancel_url": f"http://{host}/?cancelled=1",
                "line_items[0][price_data][currency]": "usd",
                "line_items[0][price_data][recurring][interval]": "month",
                "line_items[0][price_data][unit_amount]": str(cents),
                "line_items[0][price_data][product_data][name]": f"BeanBadge {name}",
                "line_items[0][quantity]": "1",
            }
            try:
                req = urllib.request.Request("https://api.stripe.com/v1/checkout/sessions", data=urllib.parse.urlencode(data).encode(),
                                             headers={"Authorization": "Bearer " + key})
                with urllib.request.urlopen(req, timeout=20) as r:
                    return self._json({"url": json.loads(r.read())["url"]})
            except Exception as e:
                return self._json({"error": f"stripe: {e}"}, 502)
        if p == "/api/subscribe":
            key = os.environ.get("RESEND_API_KEY", "")
            if not key:
                return self._json({"error": "email unconnected: RESEND_API_KEY is not set. Address was not stored."}, 400)
            email = (body.get("email", "") or "").strip()
            if "@" not in email:
                return self._json({"error": "invalid email"}, 400)
            payload = json.dumps({"from": os.environ.get("FROM_EMAIL", "onboarding@resend.dev"),
                                  "to": [email], "subject": "BeanBadge — you are on the roast list",
                                  "text": "Welcome to BeanBadge! First roast ships Tuesday. (Fictional demo.)"}).encode()
            try:
                req = urllib.request.Request("https://api.resend.com/emails", data=payload,
                                             headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    rid = json.loads(r.read()).get("id", "")
                return self._json({"ok": True, "id": rid})
            except Exception as e:
                return self._json({"error": f"resend: {e}"}, 502)
        return self.send_error(404)


if __name__ == "__main__":
    print(f"beanbadge demo on http://{HOST}:{PORT} (domain pick {DOMAIN}, check-only)", flush=True)
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()
