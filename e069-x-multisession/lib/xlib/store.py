"""Append-only store: data/<id>/items.jsonl + output per-account latest.json (e064 shape)."""
import json, time
from pathlib import Path

def append_items(root, account_id, items):
    d = Path(root) / "data" / account_id
    d.mkdir(parents=True, exist_ok=True)
    p = d / "items.jsonl"
    seen = set()
    if p.exists():
        for line in p.read_text().splitlines():
            try:
                seen.add(json.loads(line)["id"])
            except Exception:
                pass
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    added = 0
    with p.open("a") as f:
        for it in items:
            if it.get("id") in seen:
                continue
            it.setdefault("synced_at", now)
            f.write(json.dumps(it) + "\n")
            added += 1
    return {"added": added}

def publish_latest(root, account_id, max_items=500):
    d = Path(root) / "data" / account_id / "items.jsonl"
    items = []
    if d.exists():
        for line in d.read_text().splitlines()[-max_items:]:
            try:
                items.append(json.loads(line))
            except Exception:
                pass
    out = Path(root) / "output" / account_id / "latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(items, indent=2))
    return {"count": len(items), "path": str(out)}
