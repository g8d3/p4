"""X search through the live session."""
import subprocess, urllib.parse

def _run(*args):
    return subprocess.run(["agent-browser", *args], capture_output=True, text=True)

def query(account, q, count=20):
    sid = account["id"]
    url = "https://x.com/search?q=" + urllib.parse.quote(q) + "&src=typed_query&f=live"
    _run("open", url, "--session", sid)
    _run("wait", "--load", "networkidle", "--session", sid)
    snap = _run("snapshot", "--session", sid).stdout or ""
    lines = [l.strip() for l in snap.splitlines() if l.strip()]
    return {"account": sid, "q": q, "snapshot_lines": len(lines), "preview": lines[:40]}
