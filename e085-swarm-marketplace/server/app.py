#!/usr/bin/env python3
"""e085 swarm marketplace v2 — stdlib only. REAL workflow, zero mocks:

open -> delivered -> accepted | disputed -> released/refunded
- Buyer orders at agreed price (funded=false until Stripe pays).
- Seller MUST deliver (text/link) before buyer can accept. No vapor.
- Accept releases payout-owed to seller; dispute freezes for resolution.
- Reviews recompute swarm rating. Trials are priced-$0 real orders.
- Stripe Checkout + webhook verification activate with STRIPE_SECRET_KEY.
  Until then orders are honest unfunded requests (funded=false on screen).
- Auth: handle sign-in (localStorage) today; Clerk Google activates with
  CLERK_PUBLISHABLE_KEY (/api/auth tells the frontend).
TLS via box tailnet cert unless E085_TLS=0. See AGENTS.md + needs.json."""
import hashlib, json, os, re, secrets, ssl, sys, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEEDS = json.loads((ROOT / "needs.json").read_text())
PORT = int(os.environ.get(NEEDS.get("port_env", "E085_PORT"), NEEDS.get("port", 8335)))
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
SWARMS_F = DATA / "swarms.json"
ORDERS_F = DATA / "orders.jsonl"
NEEDS_F = DATA / "needs.json"
REVIEWS_F = DATA / "reviews.jsonl"
TRIALS_F = DATA / "trials.jsonl"
JOBS_F = DATA / "jobs.jsonl"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from keys import store
def stripe_key(): return store.get("STRIPE_SECRET_KEY")
def clerk_key(): return store.get("CLERK_PUBLISHABLE_KEY")
def checkout_mode(): return "live" if stripe_key() else "unconnected"
PUBLIC_URL = os.environ.get(NEEDS.get("public_url_env", "E085_PUBLIC_URL"), "")
TLS_CONF = NEEDS.get("tls", {})
TLS_CRT = os.path.expanduser(os.environ.get(TLS_CONF.get("crt_env", "E085_TLS_CRT"), "") or TLS_CONF.get("crt", "~/.config/e062/tail.crt"))
TLS_KEY = os.path.expanduser(os.environ.get(TLS_CONF.get("key_env", "E085_TLS_KEY"), "") or TLS_CONF.get("key", "~/.config/e062/tail.key"))


# No seed data: the market starts empty. Every listing is a real publish.
if not SWARMS_F.exists():
    SWARMS_F.write_text("[]")

def load_swarms():
    try: return json.loads(SWARMS_F.read_text())
    except Exception: return []
def _atomic_write(f, text):
    tmp = f.with_suffix(f.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(f)
def save_swarms(r): _atomic_write(SWARMS_F, json.dumps(r, indent=2))
def read_lines(f):
    if not f.exists(): return []
    out = []
    for line in f.read_text().splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out
def write_lines(f, rows):
    _atomic_write(f, "".join(json.dumps(o) + "\n" for o in rows))
def fee_math(price, qty=1):
    bps = NEEDS.get("fee_bps", 500)
    gross = round(float(price) * float(qty), 2)
    fee = round(gross * bps / 10000, 2)
    return gross, fee, round(gross - fee, 2)
def recompute_rating(swarm_id):
    revs = [r for r in read_lines(REVIEWS_F) if r.get("swarm_id") == swarm_id]
    if not revs: return
    rows = load_swarms()
    for r in rows:
        if r["id"] == swarm_id:
            r["rating"] = round(sum(x["stars"] for x in revs) / len(revs), 1)
    save_swarms(rows)
def stripe_api(path, params):
    """Real Stripe call (urllib, secret-key basic auth). Raises on error."""
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request("https://api.stripe.com" + path, data=data,
        headers={"Authorization": "Bearer " + stripe_key()})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

USERS_F = DATA / "users.json"
SESS_F = DATA / "sessions.json"
def load_users():
    try:
        d = json.loads(USERS_F.read_text())
        return d if isinstance(d, dict) else {}
    except Exception: return {}
def save_users(d): _atomic_write(USERS_F, json.dumps(d))
def load_sessions():
    try:
        d = json.loads(SESS_F.read_text())
        return d if isinstance(d, dict) else {}
    except Exception: return {}
def save_sessions(d): _atomic_write(SESS_F, json.dumps(d))
def clean_handle(h):
    return re.sub(r"[^a-z0-9_-]", "", (h or "").strip().lower())[:30]
def hash_pw(pw, salt=None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200000).hex()
    return salt, h
def provision_steps():
    pres = store.presence()
    live = lambda k: pres.get(k) == "live"
    return [
        {"step": "Card payment + payouts (Stripe)", "live": live("STRIPE_SECRET_KEY")},
        {"step": "Google login on your site (Clerk)", "live": live("CLERK_PUBLISHABLE_KEY")},
        {"step": "Receipt emails (Resend)", "live": live("RESEND_API_KEY")},
        {"step": "Domain DNS auto-point (Porkbun; you buy the domain once, the swarm wires it)", "live": live("PORKBUN_PAIR")},
    ]
RDAP_BOOT_F = DATA / "rdap_bootstrap.json"
_RDAP_BASES = {}
def rdap_bases():
    global _RDAP_BASES
    if _RDAP_BASES: return _RDAP_BASES
    try:
        if RDAP_BOOT_F.exists() and int(time.time()) - int(RDAP_BOOT_F.stat().st_mtime) < 7 * 86400:
            doc = json.loads(RDAP_BOOT_F.read_text())
        else:
            req = urllib.request.Request("https://data.iana.org/rdap/dns.json", headers={"User-Agent": "e085/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                doc = json.loads(r.read().decode())
            RDAP_BOOT_F.write_text(json.dumps(doc))
        for tlds, urls in doc.get("services", []):
            for t in tlds:
                _RDAP_BASES[t.lower()] = urls
    except Exception:
        pass
    return _RDAP_BASES
def rdap_one(name):
    tld = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    bases = [b if b.endswith("/") else b + "/" for b in rdap_bases().get(tld, [])] or ["https://rdap.org/domain/"]
    last = None
    for base in bases[:2]:
        url = base + ("" if base.endswith("domain/") else "domain/") + urllib.parse.quote(name)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "e085/1.0"})
            with urllib.request.urlopen(req, timeout=10):
                return {"name": name, "available": False}
        except Exception as e:
            last = e
            if "404" in str(e): return {"name": name, "available": True}
    return {"name": name, "available": None}
_SUG_CACHE = {}
def suggest_names(words):
    bases = []
    for w in words[:3]:
        w = re.sub(r"[^a-z0-9]", "", w.lower())[:20]
        if len(w) >= 3: bases.append(w)
    if not bases: return []
    per = max(6, 20 // len(bases))
    cands = []
    for b in bases:
        got = 0
        for tld in ("cc", "co", "com", "io"):
            for v in (b, b + "ly", "get" + b, b + "hub", "try" + b, b + "loop", b + "bay"):
                if got >= per: break
                n = f"{v}.{tld}"
                if n not in cands: cands.append(n); got += 1
            if got >= per: break
    if len(bases) >= 2:
        j = bases[0] + bases[1]
        for tld in ("cc", "com"):
            if len(cands) < 20 and f"{j}.{tld}" not in cands: cands.append(f"{j}.{tld}")
    return cands[:20]
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, obj, code=200, extra=None):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        for k, v in (extra or []): self.send_header(k, v)
        self.end_headers(); self.wfile.write(b)
    def _file(self, rel, ctype):
        p = ROOT / rel
        if not p.exists(): self.send_error(404); return
        b = p.read_bytes()
        self.send_response(200); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def _me(self):
        c = self.headers.get("Cookie", "") or ""
        tok = ""
        for part in c.split(";"):
            if part.strip().startswith("sm_session="):
                tok = part.strip().split("=", 1)[1].strip(); break
        if not tok: return ""
        s = load_sessions().get(tok)
        if not s or int(time.time()) - s.get("ts", 0) > 30 * 86400: return ""
        return s.get("handle", "")
    def _who(self, body, key, default="guest"):
        me = self._me()
        if me: return me
        return str(body.get(key, default) or default)[:40]
    def _sess_cookie(self, tok, age=30 * 86400):
        return [("Set-Cookie", f"sm_session={tok}; HttpOnly; Path=/; SameSite=Lax; Max-Age={age}")]
    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        try: return json.loads(self.rfile.read(n or 0) or b"{}")
        except Exception: return {}
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path in ("/", "/index.html"): return self._file("public/index.html", "text/html; charset=utf-8")
        if u.path == "/api/health":
            return self._json({"ok": True, "swarms": len(load_swarms()), "orders": len(read_lines(ORDERS_F)),
                "fee_bps": NEEDS.get("fee_bps"), "checkout": checkout_mode(), "keys_live": sum(1 for s in store.presence().values() if s == "live"), "build": "e085-v2",
                "keys": {k: (v == "live") for k, v in store.presence().items()}})
        if u.path == "/api/me":
            me = self._me()
            return self._json({"handle": me or None, "auth": "builtin"})
        if u.path == "/api/auth":
            ck = clerk_key()
            return self._json({"clerk": bool(ck), "clerk_key": ck or None})
        if u.path == "/api/keys/status":
            return self._json(store.status())
        if u.path == "/api/swarms":
            revs = read_lines(REVIEWS_F)
            counts = {}
            for r in revs: counts[r.get("swarm_id", "")] = counts.get(r.get("swarm_id", ""), 0) + 1
            out = []
            for s in load_swarms():
                s = dict(s); s["n_reviews"] = counts.get(s["id"], 0)
                out.append(s)
            return self._json(out)
        if u.path == "/api/models": return self._json(NEEDS.get("pricing_models", []))
        if u.path == "/api/orders":
            orders = read_lines(ORDERS_F)
            buyer = (q.get("buyer") or [""])[0]
            if buyer: orders = [o for o in orders if o.get("buyer") == buyer]
            return self._json(orders)
        if u.path == "/api/inbox":
            by = (q.get("by") or [""])[0]
            swarms = {r["id"]: r for r in load_swarms()}
            mine = [sid for sid, r in swarms.items() if r.get("by") == by]
            return self._json([o for o in read_lines(ORDERS_F) if o.get("swarm_id") in mine])
        if u.path == "/api/seller":
            by = (q.get("by") or [""])[0]
            swarms = {r["id"]: r for r in load_swarms()}
            mine = [sid for sid, r in swarms.items() if r.get("by") == by]
            orders = [o for o in read_lines(ORDERS_F) if o.get("swarm_id") in mine]
            owed = round(sum(o.get("net", 0) for o in orders if o.get("status") in ("accepted", "released")), 2)
            open_ = round(sum(o.get("net", 0) for o in orders if o.get("status") in ("open", "delivered")), 2)
            return self._json({"by": by, "swarms": mine, "orders": orders, "owed": owed, "open": open_,
                "payouts": "Paid via Stripe Connect once STRIPE_SECRET_KEY is set; until then settle with buyer directly."})
        if u.path == "/api/reviews":
            sid = (q.get("swarm_id") or [""])[0]
            return self._json([r for r in read_lines(REVIEWS_F) if not sid or r.get("swarm_id") == sid])
        if u.path == "/api/jobs":
            jobs = read_lines(JOBS_F)
            buyer = (q.get("buyer") or [""])[0]
            if buyer: jobs = [j for j in jobs if j.get("buyer") == buyer]
            return self._json(jobs)
        if u.path == "/api/needs":
            try:
                n = json.loads(NEEDS_F.read_text())
                return self._json(n if isinstance(n, list) else [])
            except Exception: return self._json([])
        if u.path == "/api/domain-suggest":
            words = [w for w in re.split(r"[^a-z0-9]+", (q.get("q") or [""])[0].lower()) if len(w) > 2][:3]
            if not words: return self._json({"error": "give ?q=coffee+bikes"}, 400)
            key = "+".join(sorted(words))
            hit = _SUG_CACHE.get(key)
            if hit and int(time.time()) - hit[0] < 600:
                return self._json({"q": key, "cached": True, "domains": hit[1]})
            names = suggest_names(words)
            with ThreadPoolExecutor(max_workers=2) as ex:
                out = list(ex.map(rdap_one, names))
            unknown = [r["name"] for r in out if r["available"] is None]
            if unknown:
                time.sleep(2)
                with ThreadPoolExecutor(max_workers=2) as ex:
                    retry = {r["name"]: r for r in ex.map(rdap_one, unknown)}
                out = [retry.get(r["name"], r) if r["available"] is None else r for r in out]
            out.sort(key=lambda r: (r["available"] is not True, r["available"] is None, r["name"]))
            _SUG_CACHE[key] = (int(time.time()), out)
            return self._json({"q": key, "cached": False, "domains": out})
        if u.path == "/api/domain-check":
            name = (q.get("name") or [""])[0].strip().lower()
            if not name or "." not in name: return self._json({"error": "give ?name=foo.com"}, 400)
            try:
                req = urllib.request.Request(f"https://rdap.org/domain/{urllib.parse.quote(name)}", headers={"User-Agent": "e085/1.0"})
                with urllib.request.urlopen(req, timeout=15):
                    return self._json({"name": name, "available": False, "note": "RDAP 200 = registered. Confirm at checkout."})
            except Exception as e:
                return self._json({"name": name, "available": True, "note": "No RDAP record (likely free). Confirm at checkout — RDAP absence is not a guarantee."}) if "404" in str(e) else self._json({"name": name, "available": None, "note": f"lookup failed: {e}"})
        return self.send_error(404)
    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        body = self._body()
        if u.path == "/api/auth/signup":
            h = clean_handle(body.get("handle", ""))
            pw = str(body.get("password", "") or "")
            if len(h) < 2: return self._json({"error": "handle: 2+ letters/numbers"}, 400)
            if len(pw) < 8: return self._json({"error": "password: 8+ characters"}, 400)
            users = load_users()
            if h in users: return self._json({"error": "handle taken — sign in instead"}, 409)
            salt, ph = hash_pw(pw)
            users[h] = {"salt": salt, "pw": ph, "ts": int(time.time())}
            save_users(users)
            tok = secrets.token_urlsafe(32)
            ss = load_sessions(); ss[tok] = {"handle": h, "ts": int(time.time())}; save_sessions(ss)
            return self._json({"ok": True, "handle": h}, extra=self._sess_cookie(tok))
        if u.path == "/api/auth/login":
            h = clean_handle(body.get("handle", ""))
            pw = str(body.get("password", "") or "")
            acc = load_users().get(h)
            if not acc: return self._json({"error": "no such account — create one"}, 404)
            _, ph = hash_pw(pw, acc["salt"])
            if not secrets.compare_digest(ph, acc["pw"]):
                return self._json({"error": "wrong password"}, 401)
            tok = secrets.token_urlsafe(32)
            ss = load_sessions(); ss[tok] = {"handle": h, "ts": int(time.time())}; save_sessions(ss)
            return self._json({"ok": True, "handle": h}, extra=self._sess_cookie(tok))
        if u.path == "/api/auth/logout":
            c = self.headers.get("Cookie", "") or ""
            tok = ""
            for part in c.split(";"):
                if part.strip().startswith("sm_session="):
                    tok = part.strip().split("=", 1)[1].strip(); break
            if tok:
                ss = load_sessions(); ss.pop(tok, None); save_sessions(ss)
            return self._json({"ok": True}, extra=self._sess_cookie("", age=0))
        if u.path == "/api/swarms":
            rows = load_swarms()
            valid = set(NEEDS.get("pricing_models", ["per_run"]))
            raw = str(body.get("id") or body.get("name", "swarm")).lower().replace(" ", "-")
            sid = "".join(c for c in raw if c.isalnum() or c in "-_")[:40] or f"swarm-{int(time.time())}"
            models = [m for m in (body.get("models") or ["per_run"]) if m in valid] or ["per_run"]
            pmap = body.get("price", {})
            if not isinstance(pmap, dict): pmap = {}
            price = {}
            for m in models:
                try: price[m] = float(pmap.get(m, 5.0))
                except (TypeError, ValueError): price[m] = 5.0
            old = next((r for r in rows if r["id"] == sid), {})
            row = {"id": sid, "name": str(body.get("name", sid))[:80], "by": self._who(body, "by", "you"),
                   "desc": str(body.get("desc", ""))[:500], "models": models,
                   "price": price, "url": str(body.get("url", old.get("url", "")) or "")[:500], "deal": str(body.get("deal", old.get("deal", "")) or "")[:20],
                   "rating": old.get("rating", 5.0), "runs": old.get("runs", 0)}
            rows = [r for r in rows if r["id"] != sid] + [row]
            save_swarms(rows)
            return self._json(row)
        if u.path == "/api/orders":
            rows = {r["id"]: r for r in load_swarms()}
            sid, model = body.get("swarm_id", ""), body.get("model", "per_run")
            try: qty = max(1, float(body.get("qty", 1) or 1))
            except (TypeError, ValueError): return self._json({"error": "qty must be a number"}, 400)
            if sid not in rows: return self._json({"error": "unknown swarm_id"}, 400)
            if model not in NEEDS.get("pricing_models", []): return self._json({"error": "unknown model"}, 400)
            buyer = self._who(body, "buyer")
            if rows[sid].get("by") == buyer: return self._json({"error": "you cannot order your own swarm"}, 400)
            pmap = rows[sid].get("price") or {}
            try: unit = float(pmap.get(model, 0) or 0)
            except (TypeError, ValueError): unit = 0.0
            gross, fee, net = fee_math(unit, qty)
            order = {"id": f"ord-{int(time.time()*1000)}", "swarm_id": sid, "model": model,
                     "qty": qty, "unit": unit, "gross": gross, "fee": fee, "net": net,
                     "buyer": buyer, "status": "open", "funded": False,
                     "brief": str(body.get("brief", "") or "")[:500], "ts": int(time.time())}
            with open(ORDERS_F, "a") as f: f.write(json.dumps(order) + "\n")
            rows[sid]["runs"] = rows[sid].get("runs", 0) + 1
            save_swarms(list(rows.values()))
            return self._json(order)
        if u.path == "/api/checkout":
            if not stripe_key(): return self._json({"error": "payments unconnected: paste the Stripe key on the Keys panel, then retry. Order stays open."}, 400)
            oid = body.get("order_id", "")
            orders = read_lines(ORDERS_F)
            o = next((x for x in orders if x["id"] == oid), None)
            if not o: return self._json({"error": "unknown order"}, 400)
            if o.get("funded"): return self._json({"error": "already funded"}, 400)
            base = PUBLIC_URL or f"https://{self.headers.get('Host', '')}"
            try:
                s = stripe_api("/v1/checkout/sessions", {
                    "mode": "payment", "success_url": base + "/?paid=" + oid,
                    "cancel_url": base + "/?cancelled=" + oid,
                    "client_reference_id": oid,
                    "line_items[0][price_data][currency]": "usd",
                    "line_items[0][price_data][product_data][name]": f"Swarm order {oid} ({o['swarm_id']})",
                    "line_items[0][price_data][unit_amount]": int(round(o["gross"] * 100)),
                    "line_items[0][quantity]": 1,
                    "metadata[order_id]": oid})
                return self._json({"url": s["url"]})
            except Exception as e:
                return self._json({"error": f"stripe: {e}"}, 502)
        if u.path == "/api/keys":
            if not store.check_token(body.get("token", "")): return self._json({"error": "wrong admin token (see server.log at boot)"}, 403)
            try:
                return self._json(store.save(body.get("name", ""), body.get("value", "")))
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 400)
        if u.path == "/api/keys/verify-all":
            if not store.check_token(body.get("token", "")): return self._json({"error": "wrong admin token"}, 403)
            return self._json(store.status())
        if u.path == "/api/dns/set":
            if not store.check_token(body.get("token", "")): return self._json({"error": "wrong admin token"}, 403)
            try:
                msg = store.dns_set(body.get("domain", "").strip().lower(), body.get("ip", "").strip(), body.get("rtype", "A"))
                return self._json({"ok": True, "msg": msg})
            except Exception as e:
                return self._json({"error": str(e)[:200]}, 400)
        if u.path == "/api/stripe-webhook":
            # Verify by refetching the session from Stripe (no unsigned trust).
            sid = body.get("data", {}).get("object", {}).get("id", "")
            if body.get("type") == "checkout.session.completed" and sid and stripe_key():
                try:
                    s = stripe_api(f"/v1/checkout/sessions/{urllib.parse.quote(sid)}", {})
                    if s.get("payment_status") == "paid":
                        meta = s.get("metadata") or {}
                        oid, jid = meta.get("order_id", ""), meta.get("job_id", "")
                        if oid:
                            orders = read_lines(ORDERS_F)
                            for o in orders:
                                if o["id"] == oid: o["funded"] = True
                            write_lines(ORDERS_F, orders)
                            return self._json({"ok": True, "funded": oid})
                        if jid:
                            jobs = read_lines(JOBS_F)
                            for j in jobs:
                                if j["id"] == jid:
                                    j["funded"] = True; j["status"] = "funded-swarm-dispatched"
                            write_lines(JOBS_F, jobs)
                            return self._json({"ok": True, "job": jid})
                except Exception as e:
                    return self._json({"error": f"verify failed: {e}"}, 502)
            return self._json({"ok": True, "funded": None})
        if u.path == "/api/launch":
            # ONE CLICK: buyer approves a launch (site idea + setup price).
            # Payment IS the click. On webhook-paid, a job is funded and the
            # swarm fulfills it: subdomain site live, Clerk org, Resend sender,
            # Connect account, delivery through the normal accept/dispute flow.
            # Custom domain = upgrade later (needs a registrar purchase).
            name = (body.get("site") or "").strip().lower().replace(" ", "-")[:30]
            if not name or not all(c.isalnum() or c in "-_" for c in name):
                return self._json({"error": "give your site a name (letters/numbers)"}, 400)
            buyer = self._who(body, "buyer")
            job = {"id": f"job-{int(time.time()*1000)}", "site": name,
                   "subdomain": f"{name}.{NEEDS.get('sites_domain', 'sites.local')}",
                   "brief": body.get("brief", "")[:500], "buyer": buyer,
                   "setup": float(body.get("setup", 190) or 190),
                   "status": "awaiting-payment", "funded": False, "ts": int(time.time())}
            jobs = read_lines(JOBS_F) + [job]
            write_lines(JOBS_F, jobs)
            if not stripe_key():
                return self._json({**job, "pay_url": None, "provisioning": provision_steps(),
                    "note": "payments unconnected: paste the Stripe key on the Keys panel, then launch again. Job saved."})
            base = PUBLIC_URL or f"https://{self.headers.get('Host', '')}"
            try:
                s = stripe_api("/v1/checkout/sessions", {
                    "mode": "payment", "success_url": base + "/?launched=" + job["id"],
                    "cancel_url": base + "/?cancelled=" + job["id"],
                    "client_reference_id": job["id"],
                    "line_items[0][price_data][currency]": "usd",
                    "line_items[0][price_data][product_data][name]": f"Launch {job['subdomain']}",
                    "line_items[0][price_data][unit_amount]": int(round(job["setup"] * 100)),
                    "line_items[0][quantity]": 1,
                    "metadata[job_id]": job["id"], "metadata[site]": name})
                return self._json({"id": job["id"], "pay_url": s["url"], "status": job["status"], "provisioning": provision_steps()})
            except Exception as e:
                return self._json({"error": f"stripe: {e}"}, 502)

        if u.path == "/api/deliver":
            oid = body.get("order_id", "")
            orders = read_lines(ORDERS_F)
            swarms = {r["id"]: r for r in load_swarms()}
            o = next((x for x in orders if x["id"] == oid), None)
            if not o: return self._json({"error": "unknown order"}, 400)
            if swarms.get(o["swarm_id"], {}).get("by") != self._who(body, "by", ""):
                return self._json({"error": "only the seller delivers"}, 403)
            if o.get("status") != "open": return self._json({"error": f"order is {o.get('status')}, cannot deliver"}, 400)
            text, url = str(body.get("text", ""))[:2000], str(body.get("url", ""))[:500]
            if not text.strip() and not url.strip():
                return self._json({"error": "delivery needs result text or a result link"}, 400)
            o["status"] = "delivered"
            o["delivery"] = {"text": text, "url": url, "ts": int(time.time())}
            write_lines(ORDERS_F, orders)
            return self._json({"ok": True, "status": "delivered"})
        if u.path == "/api/accept":
            oid = body.get("order_id", "")
            orders = read_lines(ORDERS_F)
            o = next((x for x in orders if x["id"] == oid), None)
            if not o: return self._json({"error": "unknown order"}, 400)
            if o.get("buyer") != self._who(body, "buyer", ""): return self._json({"error": "only the buyer accepts"}, 403)
            if o.get("status") == "open": return self._json({"error": "nothing delivered yet — accept is locked until the seller delivers"}, 400)
            if o.get("status") != "delivered": return self._json({"error": f"order is {o.get('status')}"}, 400)
            o["status"] = "accepted"
            write_lines(ORDERS_F, orders)
            return self._json({"ok": True, "status": "accepted"})
        if u.path == "/api/disputes":
            oid = body.get("order_id", "")
            orders = read_lines(ORDERS_F)
            o = next((x for x in orders if x["id"] == oid), None)
            if not o: return self._json({"error": "unknown order"}, 400)
            if o.get("buyer") != self._who(body, "buyer", ""): return self._json({"error": "only the buyer disputes"}, 403)
            if o.get("status") not in ("delivered", "open"): return self._json({"error": f"order is {o.get('status')}"}, 400)
            o["status"] = "disputed"; o["dispute_reason"] = str(body.get("reason", "") or "")[:500]
            write_lines(ORDERS_F, orders)
            return self._json({"ok": True, "status": "disputed"})
        if u.path == "/api/resolve":
            oid, outcome = body.get("order_id", ""), body.get("outcome", "release")
            orders = read_lines(ORDERS_F)
            o = next((x for x in orders if x["id"] == oid), None)
            if not o: return self._json({"error": "unknown order"}, 400)
            if o.get("status") != "disputed": return self._json({"error": "not disputed"}, 400)
            o["status"] = "released" if outcome == "release" else "refunded"
            write_lines(ORDERS_F, orders)
            return self._json({"ok": True, "status": o["status"]})
        if u.path == "/api/reviews":
            oid = body.get("order_id", "")
            orders = {o["id"]: o for o in read_lines(ORDERS_F)}
            if oid not in orders: return self._json({"error": "unknown order"}, 400)
            if orders[oid].get("status") not in ("accepted", "released"):
                return self._json({"error": "reviews open after accept/release only"}, 400)
            if any(r.get("order_id") == oid for r in read_lines(REVIEWS_F)):
                return self._json({"error": "order already reviewed"}, 400)
            try: stars = max(1, min(5, int(float(body.get("stars", 5) or 5))))
            except (TypeError, ValueError): return self._json({"error": "stars must be 1-5"}, 400)
            rev = {"swarm_id": orders[oid]["swarm_id"], "order_id": oid,
                   "stars": stars, "text": str(body.get("text", ""))[:500],
                   "ts": int(time.time())}
            with open(REVIEWS_F, "a") as f: f.write(json.dumps(rev) + "\n")
            recompute_rating(rev["swarm_id"])
            return self._json(rev)
        if u.path == "/api/trials":
            sid, buyer = body.get("swarm_id", ""), self._who(body, "buyer")
            swarms = {r["id"]: r for r in load_swarms()}
            if sid not in swarms: return self._json({"error": "unknown swarm"}, 400)
            if swarms[sid].get("by") == buyer: return self._json({"error": "you cannot trial your own swarm"}, 400)
            if any(t.get("swarm_id") == sid and t.get("buyer") == buyer for t in read_lines(TRIALS_F)):
                return self._json({"error": "trial already used for this swarm"}, 400)
            t = {"swarm_id": sid, "buyer": buyer, "ts": int(time.time())}
            with open(TRIALS_F, "a") as f: f.write(json.dumps(t) + "\n")
            o = {"id": f"ord-{int(time.time()*1000)}", "swarm_id": sid, "model": "trial",
                 "qty": 1, "unit": 0, "gross": 0, "fee": 0, "net": 0,
                 "buyer": buyer, "status": "open", "funded": True,
                 "brief": "free trial run", "ts": int(time.time())}
            with open(ORDERS_F, "a") as f: f.write(json.dumps(o) + "\n")
            return self._json({"ok": True, "order": o})
        if u.path == "/api/events":
            with open(DATA / "events.jsonl", "a") as f: f.write(json.dumps({"ts": int(time.time()), **body}) + "\n")
            return self._json({"ok": True})
        return self.send_error(404)

    def do_DELETE(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/api/auth":
            h = clean_handle((q.get("handle") or [""])[0])
            pw = (q.get("password") or [""])[0]
            users = load_users()
            acc = users.get(h)
            if not acc: return self._json({"error": "no such account"}, 404)
            _, ph = hash_pw(pw, acc["salt"])
            if not secrets.compare_digest(ph, acc["pw"]):
                return self._json({"error": "wrong password"}, 401)
            users.pop(h, None); save_users(users)
            ss = load_sessions()
            for t in [t for t, s in ss.items() if s.get("handle") == h]: ss.pop(t, None)
            save_sessions(ss)
            return self._json({"ok": True, "deleted": h})
        if u.path == "/api/swarms":
            sid = (q.get("id") or [""])[0]
            if not sid: return self._json({"error": "give ?id="}, 400)
            save_swarms([r for r in load_swarms() if r["id"] != sid])
            write_lines(REVIEWS_F, [r for r in read_lines(REVIEWS_F) if r.get("swarm_id") != sid])
            write_lines(TRIALS_F, [t for t in read_lines(TRIALS_F) if t.get("swarm_id") != sid])
            return self._json({"ok": True, "deleted": sid})
        if u.path == "/api/orders":
            oid = (q.get("id") or [""])[0]
            if not oid: return self._json({"error": "give ?id="}, 400)
            write_lines(ORDERS_F, [o for o in read_lines(ORDERS_F) if o.get("id") != oid])
            write_lines(REVIEWS_F, [r for r in read_lines(REVIEWS_F) if r.get("order_id") != oid])
            return self._json({"ok": True, "deleted": oid})
        return self.send_error(404)

if __name__ == "__main__":
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
    crt, key = TLS_CRT, TLS_KEY
    scheme = "http"
    if os.environ.get("E085_TLS", "1") != "0" and os.path.isfile(crt) and os.path.isfile(key):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(crt, key)
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
        scheme = "https"
    print(f"e085 v2 on {scheme}://0.0.0.0:{PORT} checkout={checkout_mode()} admin_token={store.token()}", flush=True)
    srv.serve_forever()
