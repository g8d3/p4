import json, os, re, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STARTED = int(time.time())
TASKS = os.path.join(ROOT, "data", "tasks.json")

def cfg():
    with open(os.path.join(ROOT, "needs.json")) as f:
        return json.load(f)

def tree(path, rel=""):
    out = []
    if not os.path.isdir(path):
        return out
    for name in sorted(os.listdir(path)):
        if name.startswith("."):
            continue
        p = os.path.join(path, name)
        r = os.path.join(rel, name)
        if os.path.isdir(p):
            out.append({"path": r, "type": "dir"})
            out.extend(tree(p, r))
        else:
            out.append({"path": r, "type": "file", "size": os.path.getsize(p)})
    return out

def read_json(p, default):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default

def write_json(p, obj):
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, p)

def read_log(n=200):
    p = os.path.join(ROOT, "data", "log.jsonl")
    if not os.path.exists(p):
        return []
    with open(p) as f:
        lines = f.readlines()[-n:]
    out = []
    for l in lines:
        try:
            out.append(json.loads(l))
        except Exception:
            pass
    return out

def read_tasks():
    return read_json(TASKS, [])


import shutil
CLK = os.sysconf("SC_CLK_TCK")
_LAST = {}
WATCH_KEYS = ("e088", "e087", "loop.sh", "http.server 8771", "blank-canvas", "server/app.py")

def host_info():
    with open("/proc/uptime") as f:
        up = float(f.read().split()[0])
    mem = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":", 1)
            if k in ("MemTotal", "MemAvailable"):
                mem[k] = int(v.split()[0])
    du = shutil.disk_usage(ROOT)
    return {"now": int(time.time()), "uptime_sec": int(up),
            "load_1_5_15": list(os.getloadavg()),
            "mem_total_mb": mem.get("MemTotal", 0) // 1024,
            "mem_avail_mb": mem.get("MemAvailable", 0) // 1024,
            "disk_total_gb": round(du.total / 1e9, 1),
            "disk_free_gb": round(du.free / 1e9, 1)}

def procs():
    global _LAST
    now = time.monotonic()
    try:
        with open("/proc/stat") as f:
            boot = int([l for l in f if l.startswith("btime")][0].split()[1])
    except Exception:
        boot = 0
    out, alive = [], set()
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            with open("/proc/%s/cmdline" % pid, "rb") as f:
                cmd = f.read().replace(b"\0", b" ").decode().strip()
        except Exception:
            continue
        if not cmd or not any(k in cmd for k in WATCH_KEYS):
            continue
        if cmd.startswith("/bin/bash -c") and not any(
                k in cmd for k in ("loop.sh", "resident", "serve.sh", "http.server")):
            continue
        try:
            st = open("/proc/%s/stat" % pid).read().rsplit(")", 1)[1].split()
            ut, stt, start = int(st[11]), int(st[12]), int(st[19])
            rss = int(open("/proc/%s/statm" % pid).read().split()[1]) * os.sysconf("SC_PAGE_SIZE") // 1048576
            state = st[0]
        except Exception:
            continue
        pt = ut + stt
        cpu = 0.0
        if pid in _LAST:
            dproc = (pt - _LAST[pid][0]) / CLK
            dwall = now - _LAST[pid][1]
            if dwall > 0:
                cpu = round(100 * dproc / dwall, 1)
        _LAST[pid] = (pt, now)
        alive.add(pid)
        out.append({"pid": int(pid), "cmd": cmd[:140], "cpu_pct": cpu,
                    "mem_mb": rss, "state": state,
                    "uptime_sec": int(time.time()) - int(boot + start / CLK)})
    for k in list(_LAST):
        if k not in alive:
            del _LAST[k]
    return {"host": host_info(), "procs": sorted(out, key=lambda e: e["pid"])}


def agent_status(name, beat):
    now = int(time.time())
    age = now - beat.get("ts", 0)
    return {"name": name, "doing": beat.get("doing", ""),
            "last_beat_sec": age, "live": age < 90}

def workers():
    now = int(time.time())
    w = read_json(os.path.join(ROOT, "data", "workers.json"), {})
    sup = w.get("supervisor", {})
    agents = w.get("agents", {})
    out = {n: agent_status(n, a) for n, a in agents.items()}
    if sup:
        sup = dict(sup)
        sup["age_sec"] = now - sup.get("ts", 0)
        sup["live"] = sup["age_sec"] < 60
    runners = read_json(os.path.join(ROOT, "data", "runners.json"), {})
    for name, r in runners.items():
        r["age_sec"] = now - r.get("ts", 0)
        r["live"] = r["age_sec"] < 120
    return {"now": now, "server_started": STARTED,
            "server_uptime_sec": now - STARTED,
            "supervisor": sup, "agents": out, "runners": runners}

def agent_detail(name):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        return None
    w = read_json(os.path.join(ROOT, "data", "workers.json"), {})
    beat = w.get("agents", {}).get(name)
    if not beat and not os.path.exists(os.path.join(ROOT, "data", "agents", name + ".json")):
        return None
    detail = read_json(os.path.join(ROOT, "data", "agents", name + ".json"), {})
    log = [e for e in read_log() if e.get("who") == name]
    iters = [v for v in read_json(os.path.join(ROOT, "data", "iterations.json"), [])
             if v.get("by") == name or v.get("who") == name or v.get("id", "").startswith(name)]
    touched, seen = [], set()
    for e in log:
        for tok in str(e.get("what", "")).replace(",", " ").split():
            if (tok.startswith("canvas/") or tok.startswith("data/")) and tok not in seen:
                seen.add(tok)
                touched.append(tok)
    files = detail.get("files", []) + [t for t in touched if t not in detail.get("files", [])]
    tasks = [t for t in read_tasks() if t.get("to") == name][-20:]
    return {"status": agent_status(name, beat or {"ts": 0}),
            "mission": detail.get("mission", ""),
            "brief": detail.get("brief", ""),
            "files": files,
            "iterations": iters,
            "tasks": tasks,
            "actions": log}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def send_json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path)
        c = cfg()
        if u.path == "/api/health":
            return self.send_json({"ok": True, "port": c["port"], "ts": int(time.time())})
        if u.path == "/api/canvas":
            return self.send_json({"tree": tree(os.path.join(ROOT, c["canvas_dir"]))})
        if u.path == "/api/activity":
            return self.send_json({"log": read_log(100)})
        if u.path == "/api/iterations":
            return self.send_json({"iterations": read_json(os.path.join(ROOT, "data", "iterations.json"), [])})
        if u.path == "/api/workers":
            return self.send_json(workers())
        if u.path == "/api/sys":
            return self.send_json(procs())
        if u.path == "/api/tasks":
            return self.send_json({"tasks": read_tasks()[-50:]})
        if u.path.startswith("/api/agent/"):
            d = agent_detail(u.path[len("/api/agent/"):])
            if d is None:
                return self.send_json({"error": "unknown agent"}, 404)
            return self.send_json(d)
        if u.path == "/" or u.path == "/index.html":
            p = os.path.join(ROOT, "public", "index.html")
            with open(p, "rb") as f:
                b = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            return self.wfile.write(b)
        self.send_response(404)
        self.end_headers()
    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/tasks":
            try:
                n = int(self.headers.get("Content-Length", 0))
            except Exception:
                n = 0
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self.send_json({"error": "bad json"}, 400)
            to = str(body.get("to", "")).strip()
            text = str(body.get("text", "")).strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]+", to) or not text:
                return self.send_json({"error": "need {to: agent-name, text: message}"}, 400)
            tasks = read_tasks()
            t = {"id": "task_%d" % int(time.time() * 1000), "to": to,
                 "text": text[:2000], "status": "pending",
                 "created": int(time.time()), "adopted_by": None, "result": None}
            tasks.append(t)
            write_json(TASKS, tasks[-200:])
            return self.send_json({"ok": True, "task": t})
        self.send_response(404)
        self.end_headers()

def main():
    c = cfg()
    srv = ThreadingHTTPServer((c["bind"], c["port"]), H)
    print(f"e088 on {c['bind']}:{c['port']}", flush=True)
    srv.serve_forever()

if __name__ == "__main__":
    main()
