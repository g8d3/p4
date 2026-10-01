"""Key store + provider verification for e085. Plain-language metadata drives
the admin Keys page; verify_* lets the SWARM auto-provision (check, wire,
activate) with zero clicks once a key exists. Secrets live in data/keys.json
(chmod 600), values never leave the server except to the provider API."""
import json, os, secrets, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
KEYS_F = DATA / "keys.json"
ADMIN_F = DATA / "admin.token"

def _get(url, headers, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "e085-keys/1.0", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def _post(url, params, headers, timeout=15):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "e085-keys/1.0", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def _post_json(url, payload, timeout=15):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "e085-keys/1.0", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def v_stripe(key):
    a = _get("https://api.stripe.com/v1/account", {"Authorization": "Bearer " + key})
    return f"taking card payments as {a.get('business_profile', {}).get('name') or a.get('email') or a.get('id')}"

def v_resend(key):
    d = _get("https://api.resend.com/v1/api_keys", {"Authorization": "Bearer " + key})
    n = len(d.get("data", [])) if isinstance(d, dict) else 0
    return f"can send receipts ({n} keys on account)"

def v_anthropic(key):
    d = _get("https://api.anthropic.com/v1/models", {"x-api-key": key, "anthropic-version": "2023-06-01"})
    return f"Claude API live ({len(d.get('data', []))} models visible)"

def v_opencode(key):
    base = os.environ.get("OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1/").rstrip("/") + "/"
    _get(base + "usage", {"Authorization": "Bearer " + key})
    return "OpenCode Zen quota reachable, spend caps apply"

def v_clerk(key):
    if not key.startswith("pk_"): raise ValueError("publishable key starts with pk_")
    return "Google button activates (shared OAuth, zero Cloud console)"

def v_porkbun(key):
    try: pair = json.loads(key)
    except Exception: raise ValueError("paste {\"apikey\": ..., \"secretapikey\": ...}")
    d = _post_json("https://api.porkbun.com/api/json/v3/ping", {"apikey": pair["apikey"], "secretapikey": pair["secretapikey"]})
    if d.get("status") != "SUCCESS": raise ValueError("porkbun rejected the pair")
    return "DNS auto-point + domain checks unlocked"

PROVIDERS = {
    "STRIPE_SECRET_KEY": {"title": "Card payments (Stripe)",
        "why": "Lets buyers pay by card. Without it, orders are recorded but money settles outside.",
        "steps": ["Open stripe.com and sign up (the ONLY account you must create yourself).", "Search settings for API keys, reveal the Secret key (sk_live_...).", "Paste it below — we verify it instantly and card payments go live."],
        "verify": v_stripe},
    "CLERK_PUBLISHABLE_KEY": {"title": "Google login (Clerk)",
        "why": "One-tap Google sign-in, no Google Cloud paperwork. Without it, buyers use a handle.",
        "steps": ["Open dashboard.clerk.com, create app called swarm-marketplace.", "Enable Google under SSO Connections (leave default shared keys).", "Copy the Publishable key (pk_test_...) and paste below."],
        "verify": v_clerk},
    "RESEND_API_KEY": {"title": "Email receipts (Resend)",
        "why": "Order confirmations and magic links. Without it, no emails go out.",
        "steps": ["Open resend.com, sign up, go to API Keys.", "Create a key, copy it (re_...).", "Paste below — we verify it with one safe read-only call."],
        "verify": v_resend},
    "PORKBUN_PAIR": {"title": "Domain autopilot (Porkbun)",
        "why": "Lets the swarm point your domain at the box itself. Without it, you copy 2 DNS lines by hand.",
        "steps": ["In Porkbun: Account → API Access → create key pair.", "Copy both keys into one box as {\"apikey\": \"...\", \"secretapikey\": \"...\"}.", "Paste below — the swarm takes DNS from there."],
        "verify": v_porkbun},
    "ANTHROPIC_API_KEY": {"title": "Claude brain (Anthropic)",
        "why": "Powers Claude-driven swarms sellers run. Only needed if you sell those.",
        "steps": ["Open console.anthropic.com, sign up, go to API keys.", "Create + copy the key (sk-ant-...).", "Paste below — we verify by listing models (free call)."],
        "verify": v_anthropic},
    "OPENCODE_API_KEY": {"title": "Agent fuel (OpenCode Zen)",
        "why": "Default inference for coding swarms, with spend caps. Sellers need this.",
        "steps": ["Open opencode.ai, fund $20 prepay.", "Copy your API key from settings.", "Paste below — we verify against the usage endpoint."],
        "verify": v_opencode},
}

class Store:
    def __init__(self):
        DATA.mkdir(exist_ok=True)
        if not KEYS_F.exists():
            KEYS_F.write_text("{}"); os.chmod(KEYS_F, 0o600)
        if not ADMIN_F.exists():
            ADMIN_F.write_text(secrets.token_urlsafe(24)); os.chmod(ADMIN_F, 0o600)
    def token(self):
        return os.environ.get("E085_ADMIN_TOKEN") or ADMIN_F.read_text().strip()
    def check_token(self, t):
        return bool(t) and secrets.compare_digest(str(t), self.token())
    def all(self):
        try: return json.loads(KEYS_F.read_text())
        except Exception: return {}
    def get(self, name):
        return self.all().get(name) or os.environ.get(name, "")
    def save(self, name, value):
        if name not in PROVIDERS: raise ValueError("unknown key slot")
        d = self.all(); d[name] = value.strip()
        KEYS_F.write_text(json.dumps(d)); os.chmod(KEYS_F, 0o600)
        return self.verify(name)
    def verify(self, name):
        key = self.get(name)
        if not key: return {"name": name, "state": "missing", "detail": "empty — paste it below"}
        try:
            return {"name": name, "state": "live", "detail": PROVIDERS[name]["verify"](key)}
        except Exception as e:
            return {"name": name, "state": "invalid", "detail": str(e)[:160]}
    def status(self):
        out = []
        for name, meta in PROVIDERS.items():
            v = self.verify(name)
            out.append({"name": name, "title": meta["title"], "why": meta["why"],
                        "steps": meta["steps"], "state": v["state"], "detail": v["detail"]})
        return out
    def presence(self):
        # No network: health/read paths use this so one page load never
        # fans out to six provider APIs. Full verify lives in status().
        return {name: ("live" if self.get(name) else "missing") for name in PROVIDERS}
    def porkbun_pair(self):
        try: return json.loads(self.get("PORKBUN_PAIR"))
        except Exception: return None
    def dns_set(self, domain, ip, rtype="A"):
        if rtype not in ("A", "AAAA", "CNAME", "TXT"):
            raise ValueError("rtype must be A, AAAA, CNAME or TXT")
        if not domain or "/" in domain or " " in domain:
            raise ValueError("bad domain")
        if not ip:
            raise ValueError("bad ip")
        pair = self.porkbun_pair()
        if not pair: raise ValueError("connect Porkbun first (paste the pair above)")
        base = {"apikey": pair["apikey"], "secretapikey": pair["secretapikey"]}
        cur = _post_json(f"https://api.porkbun.com/api/json/v3/dns/retrieve/{domain}", base)
        for r in cur.get("records", []):
            if r.get("type") == rtype and r.get("name") == domain:
                _post_json(f"https://api.porkbun.com/api/json/v3/dns/delete/{domain}/{r['id']}", base)
        d = _post_json(f"https://api.porkbun.com/api/json/v3/dns/create/{domain}",
                       {**base, "name": "@", "type": rtype, "content": ip, "ttl": 300})
        if d.get("status") != "SUCCESS": raise ValueError(str(d)[:160])
        return f"{domain} now points at {ip} (ttl 300)"

store = Store()
