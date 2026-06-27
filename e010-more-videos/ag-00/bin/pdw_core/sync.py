"""State sync for pdw."""
import subprocess
import json
from .db import DB


def sway_msg(*args):
    """Run swaymsg, return output."""
    import os
    from pathlib import Path
    
    # Find sway socket
    run_dir = Path(f"/run/user/{os.getuid()}")
    sockets = sorted(run_dir.glob("sway-ipc.*.sock"), reverse=True)
    if not sockets:
        return None
    
    env = os.environ.copy()
    env["SWAYSOCK"] = str(sockets[0])
    
    try:
        r = subprocess.run(
            ["swaymsg"] + list(args),
            capture_output=True,
            text=True,
            timeout=5,
            env=env
        )
        return json.loads(r.stdout) if r.returncode == 0 else None
    except Exception:
        return None


def get_displays():
    """Get HEADLESS displays from sway."""
    data = sway_msg("-t", "get_outputs")
    return [o["name"] for o in (data or []) if "HEADLESS" in o.get("name", "")]


def get_windows():
    """Get windows from sway."""
    data = sway_msg("-t", "get_tree")
    if not data:
        return []
    
    wins = []
    def walk(n, out="?"):
        if n.get("type") == "output": out = n.get("name", "?")
        if n.get("app_id") and n.get("pid", 0) > 0:
            wins.append({"app_id": n["app_id"], "pid": n["pid"], "display": out})
        for c in n.get("nodes", []) + n.get("floating_nodes", []):
            walk(c, out)
    walk(data)
    return wins


def pull(db: DB):
    """Sync sway state to database."""
    # Displays
    actual = set(get_displays())
    in_db = {d["name"] for d in db.q("SELECT name FROM displays WHERE status='active'")}
    
    for name in actual - in_db:
        # If display exists but is removed, reactivate it
        existing = db.q("SELECT name FROM displays WHERE name=?", (name,))
        if existing:
            db.x("UPDATE displays SET status='active' WHERE name=?", (name,))
        else:
            db.x("INSERT INTO displays (name, status) VALUES (?, 'active')", (name,))
    for name in in_db - actual:
        db.x("UPDATE displays SET status='removed' WHERE name=?", (name,))
    
    # Windows
    actual_wins = get_windows()
    db_wins = db.q("SELECT app_id, pid FROM windows")
    
    for w in db_wins:
        if not any(w["app_id"] == a["app_id"] and w["pid"] == a["pid"] for a in actual_wins):
            db.x("DELETE FROM windows WHERE app_id=? AND pid=?", (w["app_id"], w["pid"]))
    
    for w in actual_wins:
        if not any(w["app_id"] == d["app_id"] and w["pid"] == d["pid"] for d in db_wins):
            db.x("INSERT INTO windows (app_id, pid, display) VALUES (?, ?, ?)",
                 (w["app_id"], w["pid"], w["display"]))
    
    return {"displays": len(actual), "windows": len(actual_wins)}
