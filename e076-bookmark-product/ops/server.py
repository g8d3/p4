#!/usr/bin/env python3
"""e076 ops server: static hub + JSON API for inbox/run (base level).
Run: python3 ops/server.py  (serves experiment dir on :8901)
API:
  GET  /api/status            -> ops/status.json + queue info
  GET  /api/inbox             -> ops/inbox.json
  POST /api/reply {id,answer} -> records answer in ops/inbox.json
  POST /api/ask   {text}      -> human asks agent (picked up next leg)
  POST /api/run               -> triggers loop/run.sh detached (lock-guarded)
"""
import json, os, subprocess, threading, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(EXP, "ops", "inbox.json")

def load(p, d):
    try: return json.load(open(p))
    except Exception: return d

def save(p, o):
    json.dump(o, open(p, "w"), indent=1)

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw): super().__init__(*a, directory=EXP, **kw)
    def log_message(self, *a): pass
    def _send(self, o, code=200):
        b = json.dumps(o).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers()
        self.wfile.write(b)
    def _body(self):
        try: return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
        except Exception: return {}
    def do_GET(self):
        if self.path == "/api/status":
            st = load(os.path.join(EXP, "ops", "status.json"), {})
            ib = load(INBOX, [])
            st["inbox_open"] = sum(1 for m in ib if not m.get("answer"))
            st["leg_running"] = os.path.exists("/tmp/e076-runner.lock") and self._locked()
            return self._send(st)
        if self.path == "/api/inbox": return self._send(load(INBOX, []))
        if self.path == "/api/log":
            lines = []
            try:
                jl = sorted([f for f in os.listdir(os.path.join(EXP, "loop", "legs")) if f.endswith(".jsonl")])
                if jl:
                    for line in open(os.path.join(EXP, "loop", "legs", jl[-1]), errors="replace"):
                        try: d = json.loads(line)
                        except Exception: continue
                        msg = d.get("message") or {}
                        if isinstance(msg, dict):
                            for c in (msg.get("content") or []):
                                if isinstance(c, dict) and c.get("type") == "text" and c.get("text"):
                                    for t in c["text"].splitlines():
                                        t = t.strip()
                                        if t.startswith("OWNER:"):
                                            lines.append(t[6:].strip())
                    lines = lines[-5:]
            except Exception: lines = []
            return self._send({"log": lines})
        return super().do_GET()
    def do_POST(self):
        b = self._body()
        if self.path == "/api/reply":
            ib = load(INBOX, [])
            for m in ib:
                if str(m.get("id")) == str(b.get("id")):
                    m["answer"] = b.get("answer", ""); m["answered_at"] = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            save(INBOX, ib); return self._send({"ok": True})
        if self.path == "/api/ask":
            ib = load(INBOX, [])
            ib.append({"id": int(time.time()), "from": "human", "text": b.get("text", "")[:5000],
                       "created": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())})
            save(INBOX, ib); return self._send({"ok": True})
        if self.path == "/api/run":
            if self._locked(): return self._send({"ok": False, "why": "leg already running"})
            subprocess.Popen(["nohup", os.path.join(EXP, "loop", "run.sh")],
                             stdout=open(os.path.join(EXP, "loop", "runner.log"), "ab"),
                             stderr=subprocess.STDOUT, start_new_session=True)
            return self._send({"ok": True})
        return self._send({"ok": False}, 404)
    def _locked(self):
        try:
            import fcntl
            f = open("/tmp/e076-runner.lock", "w")
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(f, fcntl.LOCK_UN); return False
        except Exception: return True

def _leg_locked():
    try:
        import fcntl
        f = open("/tmp/e076-runner.lock", "w")
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(f, fcntl.LOCK_UN); return False
    except Exception: return True

def watcher():
    """Real cycle: new human messages auto-start a leg. No button needed."""
    import time as _t
    while True:
        try:
            ib = load(INBOX, [])
            fresh = [m for m in ib if m.get("from") == "human" and not m.get("answer") and not m.get("in_leg")]
            if fresh and not _leg_locked():
                def _age(ts):
                    import datetime as _d
                    for f in ("%Y%m%dT%H%M%SZ", "%Y-%m-%dT%H:%M:%SZ"):
                        try: return _t.time() - _d.datetime.strptime(ts, f).replace(tzinfo=_d.timezone.utc).timestamp()
                        except Exception: pass
                    return 9999
                if all(_age(m.get("created", "")) > 60 for m in fresh):
                    subprocess.Popen(["nohup", os.path.join(EXP, "loop", "run.sh")],
                                     stdout=open(os.path.join(EXP, "loop", "runner.log"), "ab"),
                                     stderr=subprocess.STDOUT, start_new_session=True)
                    _t.sleep(120)  # let the leg claim messages before re-checking
        except Exception: pass
        _t.sleep(15)

AUTO_RUN = os.path.exists(os.path.join(EXP, "loop", "AUTO_RUN"))
if __name__ == "__main__":
    if not os.path.exists(INBOX): save(INBOX, [])
    if AUTO_RUN:
        threading.Thread(target=watcher, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", 8901), H).serve_forever()
