"""Session ops: login status / logout. Login itself is user-assisted (docs/LOGIN.md)."""
import subprocess, json

def _run(*args):
    return subprocess.run(["agent-browser", *args], capture_output=True, text=True)

def login_status(account):
    """Check logged-in state by loading X home and grepping the handle in snapshot."""
    sid = account["id"]
    _run("open", "https://x.com/home", "--session", sid)
    _run("wait", "--load", "networkidle", "--session", sid)
    snap = _run("snapshot", "--session", sid).stdout or ""
    handle = account.get("handle", "").lstrip("@").lower()
    low = snap.lower()
    if handle and handle in low:
        return {"status": "ok", "handle": account["handle"]}
    if "log in" in low and "sign up" in low and len(snap) < 4000:
        return {"status": "expired"}
    if "captcha" in low or "challenge" in low or "unusual activity" in low:
        return {"status": "blocked"}
    return {"status": "expired", "hint": snap[:200]}

def logout(account):
    """Log out via X settings page (keeps profile dir, clears X session)."""
    sid = account["id"]
    _run("open", "https://x.com/logout", "--session", sid)
    _run("wait", "--load", "networkidle", "--session", sid)
    return {"status": "logged-out"}
