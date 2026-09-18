"""Account registry: id/handle/backend/profile only. No secrets ever."""
import json
from pathlib import Path

BACKENDS = ("chrome", "undetected", "camoufox")

def registry_path(root="."):
    return Path(root) / "accounts.json"

def load_registry(root="."):
    p = registry_path(root)
    if not p.exists():
        return {"accounts": []}
    return json.loads(p.read_text())

def save_registry(reg, root="."):
    registry_path(root).write_text(json.dumps(reg, indent=2) + "\n")

def get_account(reg, account_id):
    for a in reg["accounts"]:
        if a["id"] == account_id:
            return a
    raise KeyError(f"unknown account: {account_id}")

def add_account(reg, account_id, handle, backend="chrome", root="."):
    if backend not in BACKENDS:
        raise ValueError(f"backend must be one of {BACKENDS}")
    if any(a["id"] == account_id for a in reg["accounts"]):
        raise ValueError(f"account exists: {account_id}")
    reg["accounts"].append({
        "id": account_id,
        "handle": handle,
        "backend": backend,
        "profile": f"profiles/{account_id}",
        "status": "never",
    })
    save_registry(reg, root=root)
    return reg["accounts"][-1]
