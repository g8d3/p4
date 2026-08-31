"""Referral presets for major registrars + share-link helper."""
from __future__ import annotations
import json
import time
import secrets
from pathlib import Path

# Major registrars with affiliate programs (templates with {domain} placeholder)
# Affiliate signup links are manual — can't auto-create via API (requires human approval on Impact/CJ etc.)
REGISTRARS = [
    {
        "id": "porkbun",
        "label": "Porkbun",
        "template": "https://porkbun.com/checkout/search?q={domain}",
        "referral_hint": "Porkbun no tiene afiliados públicos — deja el template tal cual, o usa ?coupon=CODE si tienes cupón",
        "signup_url": "https://porkbun.com/products/web_hosting",  # placeholder — no affiliate
        "has_affiliate": False,
        "docs": "https://kb.porkbun.com/article/47-how-to-use-a-coupon-code",
    },
    {
        "id": "namecheap",
        "label": "Namecheap (Impact)",
        "template": "https://www.namecheap.com/domains/registration/results/?domain={domain}",
        "referral_hint": "Únete en Impact.com → aprueban en 1-2 días → tu link será https://www.namecheap.com/domains/registration/results/?domain={domain}&aff=TU_ID",
        "signup_url": "https://www.namecheap.com/promos/affiliates/",
        "has_affiliate": True,
        "docs": "https://www.namecheap.com/promos/affiliates/",
    },
    {
        "id": "godaddy",
        "label": "GoDaddy (CJ Affiliate)",
        "template": "https://www.godaddy.com/domainsearch/find?domainToCheck={domain}",
        "referral_hint": "Commission Junction → GoDaddy affiliate → link con aff ID",
        "signup_url": "https://www.godaddy.com/affiliate-program",
        "has_affiliate": True,
        "docs": "https://www.godaddy.com/affiliate-program",
    },
    {
        "id": "namesilo",
        "label": "NameSilo",
        "template": "https://www.namesilo.com/domain/search-domains?query={domain}",
        "referral_hint": "Programa de referidos interno → tu código en Account → Referral",
        "signup_url": "https://www.namesilo.com/support/v2/referral-program",
        "has_affiliate": True,
        "docs": "https://www.namesilo.com/support/v2/referral-program",
    },
    {
        "id": "cloudflare",
        "label": "Cloudflare Registrar",
        "template": "https://www.cloudflare.com/products/registrar/#search={domain}",
        "referral_hint": "Cloudflare no paga afiliados (precio costo) — útil si quieres precio honesto sin referido",
        "signup_url": "https://www.cloudflare.com/products/registrar/",
        "has_affiliate": False,
        "docs": "https://developers.cloudflare.com/registrar/",
    },
    {
        "id": "dynadot",
        "label": "Dynadot",
        "template": "https://www.dynadot.com/domain/search.html?domain={domain}",
        "referral_hint": "Afiliados via ShareASale",
        "signup_url": "https://www.dynadot.com/domain/affiliate.html",
        "has_affiliate": True,
        "docs": "https://www.dynadot.com/domain/affiliate.html",
    },
    {
        "id": "gandi",
        "label": "Gandi",
        "template": "https://shop.gandi.net/en/domain/suggest?search={domain}",
        "referral_hint": "Programa Gandi reseller, no afiliado clásico",
        "signup_url": "https://www.gandi.net/en/domain",
        "has_affiliate": False,
        "docs": "https://www.gandi.net/en/domain",
    },
]

SHARE_PATH = Path(__file__).parent.parent / "data" / "referral_shares.json"

def list_registrars():
    return REGISTRARS

def get_registrar(rid: str):
    for r in REGISTRARS:
        if r["id"] == rid:
            return r
    return None

def _load_shares():
    if SHARE_PATH.exists():
        try:
            return json.loads(SHARE_PATH.read_text())
        except: return {}
    return {}

def _save_shares(d):
    SHARE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SHARE_PATH.write_text(json.dumps(d, indent=2))

def create_share(template: str, registrar_name: str, owner: str = "anon") -> str:
    """Create a short share code that encodes the referral template. Returns code."""
    code = secrets.token_hex(3)  # 6 chars
    data = _load_shares()
    data[code] = {"template": template, "registrar_name": registrar_name, "owner": owner, "created_at": int(time.time()), "hits": 0}
    _save_shares(data)
    return code

def get_share(code: str):
    data = _load_shares()
    entry = data.get(code)
    if entry:
        # bump hits
        entry["hits"] = entry.get("hits", 0) + 1
        _save_shares(data)
    return entry

def list_shares(limit=20):
    data = _load_shares()
    # sort by hits
    items = sorted(data.items(), key=lambda x: x[1].get("hits",0), reverse=True)
    return [{"code": k, **v} for k,v in items[:limit]]
