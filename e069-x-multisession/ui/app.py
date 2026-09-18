"""e069 Web UI: multi-account X console (FastAPI, stdlib-first)."""
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
from xlib import accounts, sessions, extract, search
from xlib import browsers

app = FastAPI(title="e069 X Multisession")
PORT = 8343

@app.get("/", response_class=HTMLResponse)
def index():
    reg = accounts.load_registry(ROOT)
    cards = "".join(
        f"<div><b>{a['id']}</b> {a['handle']} [{a['backend']}] status={a['status']} "
        f"<a href='/api/status/{a['id']}'>status</a> "
        f"<a href='/api/likes/{a['id']}'>likes</a> "
        f"<a href='/api/bookmarks/{a['id']}'>bookmarks</a></div>"
        for a in reg["accounts"]
    ) or "<p>No accounts yet. POST /api/accounts {id, handle, backend}.</p>"
    return f"""<html><body><h1>e069 X Multisession</h1>{cards}
    <form action="/api/search/OWNER?q=" method="get"><input name="q" placeholder="search X">
    <button>Search (set account in URL)</button></form></body></html>"""

@app.get("/api/accounts")
def list_accounts():
    return accounts.load_registry(ROOT)

@app.post("/api/accounts")
def add_account(body: dict):
    reg = accounts.load_registry(ROOT)
    a = accounts.add_account(reg, body["id"], body["handle"],
                             body.get("backend", "chrome"), root=ROOT)
    return a

@app.post("/api/launch/{aid}")
def launch(aid: str):
    reg = accounts.load_registry(ROOT)
    return {"session": browsers.launch(accounts.get_account(reg, aid), root=ROOT)}

@app.get("/api/status/{aid}")
def status(aid: str):
    reg = accounts.load_registry(ROOT)
    a = accounts.get_account(reg, aid)
    st = sessions.login_status(a)
    a["status"] = st["status"]
    accounts.save_registry(reg, root=ROOT)
    return st

@app.post("/api/logout/{aid}")
def logout(aid: str):
    reg = accounts.load_registry(ROOT)
    return sessions.logout(accounts.get_account(reg, aid))

@app.get("/api/likes/{aid}")
def likes(aid: str):
    reg = accounts.load_registry(ROOT)
    return extract.likes(accounts.get_account(reg, aid))

@app.get("/api/bookmarks/{aid}")
def bookmarks(aid: str):
    reg = accounts.load_registry(ROOT)
    return extract.bookmarks(accounts.get_account(reg, aid))

@app.get("/api/search/{aid}")
def s(aid: str, q: str):
    reg = accounts.load_registry(ROOT)
    return search.query(accounts.get_account(reg, aid), q)
