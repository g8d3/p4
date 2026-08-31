"""Admin config storage with env-var interpolation."""
from __future__ import annotations
from pathlib import Path
import json
import os
import re

CONFIG_PATH = Path(__file__).parent.parent / "data" / "config.json"
TOKENS_PATH = Path(__file__).parent.parent / "data" / "admin_tokens.json"

DEFAULT_CONFIG = {
    "admin_password": "admin123",
    "registrar_template": "https://porkbun.com/checkout/search?q={domain}",
    "registrar_name": "Porkbun",
    "referral_code": "",
    "ai_provider": "opencode-go",
    "ai_base_url": "${OPENCODE_GO_BASE_URL}",
    "ai_model": "muse-spark-1.2-contributor",
    "ai_api_key": "${OPENCODE_GO_API_KEY}",
}

# Expand ${VAR} and $VAR and ${VAR:-default} using env
_ENV_RE = re.compile(r"\$\{([^}:]+)(?::-([^}]*))?\}|\$([A-Za-z_][A-Za-z0-9_]*)")

def _expand_env(value: str) -> str:
    if not isinstance(value, str):
        return value
    # Use os.path.expandvars first for simple cases, then handle ${VAR:-default}
    def repl(m):
        if m.group(3):  # $VAR
            return os.environ.get(m.group(3), "")
        var = m.group(1)
        default = m.group(2)
        v = os.environ.get(var)
        if v is None or v == "":
            return default if default is not None else ""
        return v
    # Expand until stable (max 3 iterations for nested)
    for _ in range(3):
        new = _ENV_RE.sub(repl, value)
        if new == value:
            break
        value = new
    return value

def resolve_value(value):
    if isinstance(value, str) and ("$" in value):
        return _expand_env(value)
    return value

def resolve_config(cfg: dict) -> dict:
    """Return cfg with env vars expanded."""
    out = {}
    for k, v in cfg.items():
        out[k] = resolve_value(v) if isinstance(v, str) else v
    return out

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text())
            for k, v in DEFAULT_CONFIG.items():
                data.setdefault(k, v)
            return data
        except:
            pass
    return dict(DEFAULT_CONFIG)

def load_resolved_config() -> dict:
    return resolve_config(load_config())

def save_config(cfg: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))

def get_public_config() -> dict:
    cfg = load_config()
    resolved = resolve_config(cfg)
    has_key = bool((resolved.get("ai_api_key") or "").strip())
    # also consider raw env fallback
    if not has_key:
        has_key = bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENCODE_GO_API_KEY") or os.environ.get("OPENCODE_API_KEY"))
    return {
        "registrar_template": cfg.get("registrar_template"),
        "registrar_name": cfg.get("registrar_name"),
        "referral_code": cfg.get("referral_code"),
        "ai_provider": cfg.get("ai_provider"),
        "ai_model": cfg.get("ai_model"),
        "ai_model_resolved": resolved.get("ai_model"),
        "ai_base_url": cfg.get("ai_base_url"),
        "ai_base_url_resolved": resolved.get("ai_base_url"),
        "has_ai_key": has_key,
        "has_ai_key_raw": bool((cfg.get("ai_api_key") or "").strip()),
        "ai_api_key_preview": (resolved.get("ai_api_key") or "")[:6] + "***" if has_key else "",
    }

# ----- Admin tokens -----
import time, secrets

def _load_tokens() -> dict:
    if TOKENS_PATH.exists():
        try:
            return json.loads(TOKENS_PATH.read_text())
        except: return {}
    return {}

def _save_tokens(d: dict):
    TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKENS_PATH.write_text(json.dumps(d, indent=2))

def create_admin_token() -> str:
    tok = secrets.token_hex(32)
    data = _load_tokens()
    data[tok] = {"created_at": int(time.time()), "expires_at": int(time.time()) + 24*3600}
    _save_tokens(data)
    return tok

def verify_admin_token(tok: str) -> bool:
    if not tok: return False
    data = _load_tokens()
    entry = data.get(tok)
    if not entry: return False
    if entry["expires_at"] < time.time():
        data.pop(tok, None)
        _save_tokens(data)
        return False
    return True

def verify_admin_request(x_admin_password: str = None, x_admin_token: str = None) -> bool:
    cfg = load_config()
    if x_admin_token and verify_admin_token(x_admin_token):
        return True
    if x_admin_password and x_admin_password == cfg.get("admin_password"):
        return True
    return False
