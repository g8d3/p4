"""Extract likes + bookmarks through the live session (ambient authority).

Recipe (browser-extract skill): open page, wait networkidle, list xhr/fetch,
pull full response bodies, verify against snapshot. Never replay via curl.
"""
import subprocess, json

def _run(*args):
    return subprocess.run(["agent-browser", *args], capture_output=True, text=True)

def _xhr_ids(sid, needle):
    out = _run("network", "requests", "--type", "xhr,fetch", "--session", sid).stdout or ""
    ids = []
    for line in out.splitlines():
        if needle.lower() in line.lower():
            tok = line.strip().split()
            if tok:
                ids.append(tok[0])
    return ids

def _body(sid, rid):
    out = _run("network", "request", rid, "--session", sid, "--json").stdout or "{}"
    try:
        return json.loads(out)["data"]["responseBody"]
    except Exception:
        return out

def likes(account, since_id=None, limit=100):
    sid = account["id"]
    handle = account["handle"].lstrip("@")
    _run("open", f"https://x.com/{handle}/likes", "--session", sid)
    _run("wait", "--load", "networkidle", "--session", sid)
    ids = _xhr_ids(sid, "Likes") or _xhr_ids(sid, "graphql")
    rows = []
    for rid in ids[:3]:
        body = _body(sid, rid)
        rows.append({"request": rid, "bytes": len(body)})
    return {"account": sid, "calls": rows, "note": "parse tweet objects from bodies; verify via snapshot"}

def bookmarks(account, since_id=None, limit=100):
    sid = account["id"]
    _run("open", "https://x.com/i/bookmarks", "--session", sid)
    _run("wait", "--load", "networkidle", "--session", sid)
    ids = _xhr_ids(sid, "Bookmark") or _xhr_ids(sid, "graphql")
    rows = []
    for rid in ids[:3]:
        body = _body(sid, rid)
        rows.append({"request": rid, "bytes": len(body)})
    return {"account": sid, "calls": rows, "note": "parse tweet objects from bodies; verify via snapshot"}
