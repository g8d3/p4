"""History persistence — each generation saved."""
from __future__ import annotations
from pathlib import Path
import json
import time
import uuid

HISTORY_PATH = Path(__file__).parent.parent / "data" / "history.json"

def _load() -> list:
    if HISTORY_PATH.exists():
        try:
            return json.loads(HISTORY_PATH.read_text())
        except: return []
    return []

def _save(data: list):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(data, indent=2))

def add_entry(entry: dict) -> dict:
    entry["id"] = uuid.uuid4().hex[:8]
    entry["created_at"] = int(time.time())
    data = _load()
    data.insert(0, entry)
    # keep last 100
    data = data[:100]
    _save(data)
    return entry

def list_history(limit: int = 30) -> list:
    data = _load()
    return data[:limit]

def get_entry(entry_id: str) -> dict | None:
    for e in _load():
        if e["id"] == entry_id:
            return e
    return None

def delete_entry(entry_id: str) -> bool:
    data = _load()
    new = [e for e in data if e["id"] != entry_id]
    if len(new) != len(data):
        _save(new)
        return True
    return False
