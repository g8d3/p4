#!/usr/bin/env python3
"""e086 Agent Company OS — stdlib only. No env vars needed; settings via /api/settings."""
import json, os, time, uuid, threading, subprocess, sys, signal, shutil, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
PUB = os.path.join(ROOT, "public")
os.makedirs(DATA, exist_ok=True)

def p(name): return os.path.join(DATA, name)

def load(name, default):
    try:
        with open(p(name)) as f: return json.load(f)
    except Exception: return default

def save(name, obj):
    tmp = p(name) + ".tmp"
    with open(tmp, "w") as f: json.dump(obj, f, indent=2)
    os.replace(tmp, p(name))

def log_event(type_, detail):
    with open(p("events.jsonl"), "a") as f:
        f.write(json.dumps({"ts": int(time.time()), "type": type_, "detail": detail}) + "\n")

def seed():
    if not os.path.exists(p("settings.json")):
        with open(os.path.join(ROOT, "needs.json")) as f: needs = json.load(f)
        save("settings.json", {"port": needs["port"], "bind": needs["bind"],
            "loop_interval_sec": needs["loop_interval_sec"],
            "heartbeat_timeout_sec": needs["heartbeat_timeout_sec"],
            "min_workers": needs["min_workers"], "company_name": needs["company_name"]})
    if not os.path.exists(p("roles.json")):
        save("roles.json", [
            {"id": "ceo", "title": "CEO", "area": "leadership", "prompt": "Sets vision, prioritizes backlog, can create/redefine any role.", "essential": True},
            {"id": "board", "title": "Board of Directors", "area": "leadership", "prompt": "Approves iterations, changes org chart, hires/fires roles.", "essential": True},
            {"id": "designer", "title": "Product Designer", "area": "product", "prompt": "Designs UX flows and specs before implementation.", "essential": True},
            {"id": "implementer", "title": "Implementer", "area": "engineering", "prompt": "Writes code in small verifiable steps.", "essential": True},
            {"id": "reviewer", "title": "Reviewer / QA", "area": "engineering", "prompt": "Reviews diffs, runs e2e tests incl. UI first-paint checks.", "essential": True},
            {"id": "content", "title": "Content Creator", "area": "growth", "prompt": "Creates and posts launch content, changelogs, docs.", "essential": True},
            {"id": "provisioner", "title": "Provisioner / DevOps", "area": "ops", "prompt": "Provisions domains, deploy targets, keys, checklists.", "essential": True},
            {"id": "marketer", "title": "Marketer", "area": "growth", "prompt": "Outreach, distribution, metrics.", "essential": False},
        ])
    if not os.path.exists(p("agents.json")):
        now = int(time.time())
        save("agents.json", [
            {"id": "agent-1", "name": "Ada (implementer)", "role_id": "implementer",
             "status": "working", "current_task_id": "t2", "last_heartbeat": now,
             "note": "Seed worker — loop keeps at least 1 working."},
        ])
    if not os.path.exists(p("tasks.json")):
        save("tasks.json", [
            {"id": "t1", "title": "Design timeline UX (past/present/future)", "role_id": "designer", "state": "done", "detail": "v0 spec", "updated": int(time.time()) - 7200},
            {"id": "t2", "title": "Implement team board + loop supervisor", "role_id": "implementer", "state": "doing", "detail": "this app", "updated": int(time.time()) - 600},
            {"id": "t3", "title": "E2E review: UI first-paint + API smoke", "role_id": "reviewer", "state": "todo", "detail": "GET /api/verify", "updated": int(time.time())},
            {"id": "t4", "title": "Write launch post + changelog", "role_id": "content", "state": "todo", "detail": "draft", "updated": int(time.time())},
            {"id": "t5", "title": "Provisioning checklist (domain/deploy/keys)", "role_id": "provisioner", "state": "todo", "detail": "checklist", "updated": int(time.time())},
        ])
    if not os.path.exists(p("iterations.json")):
        save("iterations.json", [
            {"id": "v0.1.0", "title": "Seed: company OS boots itself", "state": "released",
             "notes": "Roles, team board, supervisor loop, timeline.", "ts": int(time.time()) - 3600},
        ])
    if not os.path.exists(p("loop_state.json")):
        save("loop_state.json", {"running": True, "last_tick": 0, "ticks": 0, "auto_starts": 0})
    if not os.path.exists(p("events.jsonl")):
        log_event("boot", "company OS seeded")

seed()
LOCK = threading.RLock()  # reentrant: do_POST holds it while do_tick() re-acquires
START = int(time.time())
ALLOW_FILES = {"server/app.py", "public/index.html", "needs.json", "AGENTS.md"}
SNAP = os.path.join(DATA, "snapshots")
MIME = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json"}

def settings():
    d = load("settings.json", {})
    d.setdefault("ceo_every_ticks", 30)
    d.setdefault("hold_rotate_ticks", 10)
    return d
def fresh(agent, timeout):
    return agent.get("status") == "working" and (int(time.time()) - int(agent.get("last_heartbeat", 0))) <= timeout

def self_check():
    s = settings(); to = int(s.get("heartbeat_timeout_sec", 90))
    checks = {}
    checks["settings_ok"] = bool(load("settings.json", {}).get("company_name"))
    roles = load("roles.json", []); agents = load("agents.json", [])
    checks["roles_seeded"] = len(roles) >= 3
    checks["min_workers_met"] = len([a for a in agents if fresh(a, to)]) >= int(s.get("min_workers", 1))
    try:
        with open(os.path.join(PUB, "index.html")) as f: html = f.read()
        checks["ui_first_paint"] = "Company OS" in html and "/api/timeline" in html
    except Exception: checks["ui_first_paint"] = False
    checks["iterations_exist"] = len(load("iterations.json", [])) >= 1
    return checks

def snapshot_code(sid):
    sid = "".join(c for c in str(sid) if c.isalnum() or c in ".-_")[:40] or f"s{int(time.time())}"
    dest = os.path.join(SNAP, sid)
    if os.path.exists(dest): raise ValueError("exists")
    os.makedirs(dest)
    for d in ("server", "public"): shutil.copytree(os.path.join(ROOT, d), os.path.join(dest, d))
    for f in ("needs.json", "AGENTS.md"): shutil.copy2(os.path.join(ROOT, f), os.path.join(dest, f))
    return sid

def code_mtime():
    m = 0
    for base in ("server", "public"):
        for dp, _, fns in os.walk(os.path.join(ROOT, base)):
            for fn in fns: m = max(m, os.path.getmtime(os.path.join(dp, fn)))
    for f in ("needs.json", "AGENTS.md"): m = max(m, os.path.getmtime(os.path.join(ROOT, f)))
    return int(m)

def exec_action(action, params, agent_id, tasks, iters):
    params = params or {}
    if action == "add_task":
        t = {"id": "t-" + uuid.uuid4().hex[:4], "title": params.get("title", "untitled"),
             "role_id": params.get("role_id", "implementer"), "state": "todo", "updated": int(time.time())}
        if params.get("action"): t["action"] = params["action"]; t["params"] = params.get("params", {})
        tasks.append(t)
        return f"backlog {t['id']}"
    if action == "add_role":
        roles = load("roles.json", [])
        if params.get("id") and not any(r["id"] == params["id"] for r in roles):
            roles.append({"id": params["id"], "title": params.get("title", params["id"]),
                          "area": params.get("area", "ops"), "prompt": params.get("prompt", "")})
            save("roles.json", roles)
        return f"role {params.get('id')}"
    if action == "update_settings":
        cur = load("settings.json", {}); cur.update(params); save("settings.json", cur)
        return "settings updated (restart if port changed)"
    if action == "snapshot":
        return "snapshot " + snapshot_code(params.get("id", ""))
    if action == "release":
        n = len(iters) + 1; vid = f"v0.{n}.0"
        while any(i["id"] == vid for i in iters): n += 1; vid = f"v0.{n}.0"
        iters.append({"id": vid, "title": params.get("title", "Autonomous release"), "state": "released",
                      "notes": params.get("note", f"cut by {agent_id}"), "ts": int(time.time())})
        claimed = stamp_release(tasks, vid)
        snapshot_code(vid)
        return f"released {vid} + snapshot, claimed {claimed} tasks"
    raise ValueError(f"unknown action {action}")

def stamp_release(tasks, vid):
    n = 0
    for t in tasks:
        if t.get("state") == "done" and not t.get("version"):
            t["version"] = vid; n += 1
    return n

def ceo_review(tasks, iters):
    bad = [k for k, ok in self_check().items() if not ok]
    titles = {t.get("title", "") for t in tasks if t["state"] != "done"}
    for chk in bad:
        title = f"Repair verify: {chk}"
        if title not in titles:
            tasks.append({"id": "t-" + uuid.uuid4().hex[:4], "title": title, "role_id": "reviewer",
                          "state": "todo", "detail": "raised by CEO review", "updated": int(time.time())})
            log_event("ceo", f"proposed {title}")
    try: mtime = code_mtime()
    except Exception: mtime = 0
    rel = [i.get("ts", 0) for i in iters if i.get("state") == "released"]
    if mtime > (max(rel) if rel else 0) + 5 and not any(t.get("action") == "release" and t["state"] != "done" for t in tasks):
        tasks.append({"id": "t-" + uuid.uuid4().hex[:4], "title": "Release new code changes",
                      "role_id": "ceo", "state": "todo", "action": "release", "params": {},
                      "detail": "raised by CEO review", "updated": int(time.time())})
        log_event("ceo", "proposed release of new code changes")

def touch_session(agent, by="api", event=None, task=None, outcome=None):
    ss = load("sessions.json", {})
    s = ss.get(agent["id"])
    if s is None:
        s = {"id": agent["id"], "name": agent.get("name"), "role_id": agent.get("role_id"),
             "spawned": int(time.time()), "spawned_by": by, "beats": 0, "first_beat": None,
             "last_beat": None, "tasks": [], "ended": None, "ended_why": None}
        ss[agent["id"]] = s
    s["name"] = agent.get("name", s["name"]); s["role_id"] = agent.get("role_id", s["role_id"])
    if event == "beat":
        s["beats"] = int(s.get("beats", 0)) + 1
        if not s.get("first_beat"): s["first_beat"] = int(time.time())
        s["last_beat"] = int(time.time())
    if event == "task_start" and task:
        s["tasks"].append({"task": task, "started": int(time.time()), "ended": None, "outcome": "doing"})
    if event in ("task_done", "task_failed") and task:
        closed = False
        for e in reversed(s["tasks"]):
            if e["task"] == task and not e["ended"]:
                e["ended"] = int(time.time()); e["outcome"] = event; closed = True; break
        if not closed:
            s["tasks"].append({"task": task, "started": None, "ended": int(time.time()), "outcome": event})
    if event == "held" and task:
        s["tasks"].append({"task": task, "started": None, "ended": int(time.time()), "outcome": "held (released)"})
    if event == "ended":
        s["ended"] = int(time.time()); s["ended_why"] = outcome
    save("sessions.json", ss)

def do_tick():
    """Supervisor: ensure >= min_workers fresh working agents. Returns report."""
    with LOCK:
        s = settings(); to = int(s.get("heartbeat_timeout_sec", 90)); mw = int(s.get("min_workers", 1))
        now = int(time.time())
        agents = load("agents.json", []); tasks = load("tasks.json", []); roles = load("roles.json", [])
        st = load("loop_state.json", {"running": True, "last_tick": 0, "ticks": 0, "auto_starts": 0})
        for a in list(agents):
            if a.get("status") == "working" and now - int(a.get("last_heartbeat", 0)) > to:
                touch_session(a, event="ended", outcome="reaped: heartbeat dead")
                for t in tasks:
                    if t["id"] == a.get("current_task_id") and t["state"] == "doing":
                        t["state"] = "todo"; t["updated"] = now
                        touch_session(a, event="held", task=t["id"])
                        log_event("task_freed", f"{t['id']} holder reaped -> backlog")
                agents.remove(a); log_event("agent_reap", f"{a['id']} heartbeat dead")
        working = [a for a in agents if fresh(a, to)]
        report = {"ts": int(time.time()), "working_before": len(working), "min_workers": mw, "actions": []}
        if st.get("running") and len(working) < mw:
            need = mw - len(working)
            orphans = [t for t in tasks if t["state"] == "doing" and not any(
                a.get("current_task_id") == t["id"] and fresh(a, to) for a in agents)]
            orphans.sort(key=lambda t: int(t.get("updated", 0)))
            backlog = [t for t in tasks if t["state"] == "todo" and not t.get("needs_human")]
            cover = orphans + backlog
            started = 0
            for i in range(need):
                task = cover[i] if i < len(cover) else None
                if task is None:
                    log_event("supervisor", "nothing to cover, holding fire")
                    break
                rid = (task or {}).get("role_id") or "implementer"
                if not any(r["id"] == rid for r in roles): rid = roles[0]["id"] if roles else "implementer"
                aid = "agent-" + uuid.uuid4().hex[:6]
                agents.append({"id": aid, "name": f"Auto {rid} {aid[-4:]}", "role_id": rid,
                    "status": "working", "current_task_id": (task or {}).get("id"),
                    "last_heartbeat": int(time.time()), "note": "auto-started by supervisor loop"})
                touch_session(agents[-1], by="auto")
                if task: touch_session(agents[-1], event="task_start", task=task["id"])
                if task: task["state"] = "doing"; task["updated"] = int(time.time()); task["held_ticks"] = 0
                report["actions"].append(f"started {aid} role={rid} task={(task or {}).get('id', '-')}")
                log_event("auto_start", report["actions"][-1])
                started += 1
            st["auto_starts"] = int(st.get("auto_starts", 0)) + started
        # work engine: action-tasks EXECUTE (real effects); actionless tasks hold for a real builder.
        # Idle hands pull backlog. CEO reviews on schedule. Nothing completes by theater.
        iters = load("iterations.json", [])
        attended = set()
        for a in agents:
            if not fresh(a, to): continue
            tid = a.get("current_task_id")
            t = next((x for x in tasks if x["id"] == tid and x["state"] == "doing"), None) if tid else None
            if t is None and a.get("status") == "working":
                nxt = next((x for x in tasks if x["state"] == "todo" and not x.get("needs_human")), None)
                if nxt:
                    nxt["state"] = "doing"; nxt["updated"] = now
                    a["current_task_id"] = nxt["id"]; a["last_heartbeat"] = now
                    attended.add(nxt["id"]); t = nxt
                    touch_session(a, event="task_start", task=nxt["id"])
                    log_event("task_start", f"{nxt['id']} auto-pulled by {a['id']}")
                else:
                    a["status"] = "idle"; a["current_task_id"] = None
                    log_event("agent_idle", f"{a['id']} backlog empty")
                    continue
            if t is not None and t["id"] not in attended:
                attended.add(t["id"]); t["updated"] = now
                if t.get("needs_human") and t.get("action"):
                    a["current_task_id"] = None
                    log_event("task_parked", f"{t['id']} released by holder, needs a human builder")
                    continue
                if not t.get("action"):
                    t["held_ticks"] = int(t.get("held_ticks", 0)) + 1
                    if t["held_ticks"] >= int(s.get("hold_rotate_ticks", 10)):
                        t["state"] = "todo"; t["held_ticks"] = 0; t["updated"] = now
                        a["current_task_id"] = None
                        log_event("task_rotated", f"{t['id']} held too long, back to backlog")
                        continue
                if t.get("action"):
                    try:
                        res = exec_action(t.get("action"), t.get("params") or {}, a["id"], tasks, iters)
                        t["state"] = "done"; t["result"] = res; t.pop("needs_human", None)
                        a["current_task_id"] = None; a["last_heartbeat"] = now
                        touch_session(a, event="task_done", task=t["id"])
                        log_event("task_done", f"{t['id']} executed {t['action']}: {res}")
                    except Exception as e:
                        t["fail_count"] = int(t.get("fail_count", 0)) + 1
                        a["current_task_id"] = None
                        touch_session(a, event="task_failed", task=t["id"])
                        log_event("task_failed", f"{t['id']} {t['action']}: {e}")
                        if t["fail_count"] >= 3:
                            t["needs_human"] = True
                            log_event("task_parked", f"{t['id']} needs a human builder")
        for t in tasks:
            if t["state"] == "doing" and t["id"] not in attended and now - int(t.get("updated", now)) > to:
                t["state"] = "todo"; t["updated"] = now
                log_event("stalled_back", f"{t['id']} no live agent -> backlog")
        ceo_every = int(s.get("ceo_every_ticks", 30))
        if st.get("running") and ceo_every > 0 and int(st.get("ticks", 0)) % ceo_every == 0:
            try: ceo_review(tasks, iters)
            except Exception as e: log_event("ceo_error", str(e)[:200])
        st["last_tick"] = int(time.time()); st["ticks"] = int(st.get("ticks", 0)) + 1
        save("agents.json", agents); save("tasks.json", tasks); save("loop_state.json", st); save("iterations.json", iters)
        with open(p("heartbeat.json"), "w") as f: json.dump({"last_tick": st["last_tick"]}, f)
        report.update({"working_after": len([a for a in agents if fresh(a, to)]), "tick": st["ticks"]})
        log_event("tick", f"working {report['working_before']}->{report['working_after']}")
        return report

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send_json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def body(self):
        try: return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0) or 0)) or b"{}")
        except Exception: return {}
    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path.startswith("/api/"):
            s = settings(); to = int(s.get("heartbeat_timeout_sec", 90))
            if u.path == "/api/health":
                agents = load("agents.json", [])
                return self.send_json({"ok": True, "company": s.get("company_name"),
                    "working": len([a for a in agents if fresh(a, to)]), "ts": int(time.time())})
            if u.path == "/api/settings": return self.send_json(load("settings.json", {}))
            if u.path == "/api/roles": return self.send_json(load("roles.json", []))
            if u.path == "/api/agents": return self.send_json(load("agents.json", []))
            if u.path == "/api/tasks": return self.send_json(load("tasks.json", []))
            if u.path == "/api/iterations": return self.send_json(load("iterations.json", []))
            if u.path == "/api/loop": return self.send_json({**load("loop_state.json", {}),
                "heartbeat": load("heartbeat.json", {}), "timeout_sec": to})
            if u.path == "/api/timeline":
                tasks = load("tasks.json", []); iters = load("iterations.json", [])
                agents = load("agents.json", [])
                present = [a for a in agents if fresh(a, to)]
                return self.send_json({
                    "past": {"done_tasks": [t for t in tasks if t["state"] == "done"],
                             "released": [i for i in iters if i["state"] == "released"]},
                    "present": {"working_agents": present,
                                "doing_tasks": [t for t in tasks if t["state"] == "doing"],
                                "loop": load("loop_state.json", {})},
                    "future": {"todo_tasks": [t for t in tasks if t["state"] == "todo"],
                               "planned": [i for i in iters if i["state"] != "released"]}})
            if u.path == "/api/events":
                try:
                    with open(p("events.jsonl")) as f: lines = f.readlines()[-80:]
                except Exception: lines = []
                return self.send_json([json.loads(l) for l in lines if l.strip()])
            if u.path == "/api/verify":
                checks = self_check()
                score = sum(1 for v in checks.values() if v)
                return self.send_json({"checks": checks, "score": f"{score}/{len(checks)}",
                    "pass": all(checks.values())})
            if u.path == "/api/ops":
                dp = None
                try: dp = int(open(p("loop.pid")).read().strip())
                except Exception: dp = None
                alive = False
                if dp:
                    try: os.kill(dp, 0); alive = True
                    except Exception: alive = False
                try: snaps = sorted(os.listdir(SNAP))
                except Exception: snaps = []
                return self.send_json({"pid": os.getpid(), "uptime_s": int(time.time()) - START,
                    "settings": settings(), "daemon": {"running": alive, "pid": dp},
                    "snapshots": snaps, "gate": load("gate.json", {})})
            if u.path == "/api/ops/logs":
                name = (q.get("name") or ["server"])[0]
                fmap = {"server": os.path.join(ROOT, "server.log"), "daemon": os.path.join(ROOT, "loop-daemon.log"),
                        "events": p("events.jsonl")}
                try:
                    with open(fmap.get(name, fmap["server"])) as f: lines = f.readlines()[-120:]
                except Exception as e: lines = [f"no log yet ({e})"]
                return self.send_json({"name": name, "tail": "".join(lines)[-8000:]})
            if u.path == "/api/tasklog":
                tid = (q.get("id") or [""])[0]
                rx = re.compile(r"\b" + re.escape(tid) + r"\b") if tid else None
                evs = []
                try:
                    with open(p("events.jsonl")) as f:
                        for line in f:
                            try: e = json.loads(line)
                            except Exception: continue
                            if rx and (rx.search(e.get("detail", "")) or rx.search(e.get("type", ""))): evs.append(e)
                except Exception: pass
                t = next((x for x in load("tasks.json", []) if x["id"] == tid), {})
                holders = []
                for sid, s in load("sessions.json", {}).items():
                    for h in s.get("tasks", []):
                        if h.get("task") == tid:
                            holders.append({"agent": s.get("name") or sid, "started": h.get("started"),
                                            "ended": h.get("ended"), "outcome": h.get("outcome")})
                return self.send_json({"task": t, "holders": holders, "events": evs[-40:]})
            if u.path == "/api/sessions":
                ss = load("sessions.json", {})
                live = {a["id"]: a for a in load("agents.json", [])}
                out = []
                for sid, x in ss.items():
                    d = dict(x); d["live"] = sid in live
                    if sid in live: d["status"] = live[sid].get("status")
                    out.append(d)
                out.sort(key=lambda x: x.get("spawned", 0), reverse=True)
                return self.send_json(out)
            if u.path == "/api/ops/files": return self.send_json(sorted(ALLOW_FILES))
            if u.path == "/api/ops/file":
                name = (q.get("name") or [""])[0]
                if name not in ALLOW_FILES: return self.send_json({"error": "not editable"}, 403)
                with open(os.path.join(ROOT, name)) as f: return self.send_json({"name": name, "content": f.read()})
            return self.send_json({"error": "unknown endpoint"}, 404)
        rel = u.path.lstrip("/") or "index.html"
        fp = os.path.join(PUB, rel)
        if not os.path.abspath(fp).startswith(PUB) or not os.path.isfile(fp):
            fp = os.path.join(PUB, "index.html")
        ext = os.path.splitext(fp)[1]
        with open(fp, "rb") as f: b = f.read()
        self.send_response(200); self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        u = urlparse(self.path); b = self.body()
        if u.path == "/api/ops/gate":
            try:
                r = subprocess.run(["bash", "test/check.sh"], cwd=ROOT, capture_output=True, text=True, timeout=120)
                res = {"pass": r.returncode == 0, "output": (r.stdout + r.stderr)[-6000:], "ts": int(time.time())}
            except Exception as e: res = {"pass": False, "output": str(e), "ts": int(time.time())}
            save("gate.json", res); return self.send_json(res)
        with LOCK:
            if u.path == "/api/settings":
                cur = load("settings.json", {}); cur.update(b); save("settings.json", cur)
                log_event("settings", json.dumps(b)[:200]); return self.send_json(cur)
            if u.path == "/api/roles":
                roles = load("roles.json", [])
                if b.get("delete"):
                    roles = [r for r in roles if r["id"] != b["delete"]]
                else:
                    b.setdefault("id", "role-" + uuid.uuid4().hex[:6])
                    roles = [r for r in roles if r["id"] != b["id"]] + [b]
                save("roles.json", roles); log_event("role", b.get("id", "?")); return self.send_json(roles)
            if u.path == "/api/agents":
                agents = load("agents.json", [])
                if b.get("delete"):
                    held = [a.get("current_task_id") for a in agents if a["id"] == b["delete"]]
                    vict = next((a for a in agents if a["id"] == b["delete"]), None)
                    for a in agents:
                        if a["id"] == b["delete"]: touch_session(a, event="ended", outcome="deleted")
                    agents = [a for a in agents if a["id"] != b["delete"]]
                    tasks = load("tasks.json", [])
                    for t in tasks:
                        if t["id"] in held and t["state"] == "doing":
                            t["state"] = "todo"; t["updated"] = int(time.time())
                            if vict: touch_session(vict, event="held", task=t["id"])
                            log_event("task_freed", f"{t['id']} holder deleted -> backlog")
                    save("tasks.json", tasks)
                elif b.get("heartbeat"):
                    for a in agents:
                        if a["id"] == b["heartbeat"]:
                            a["last_heartbeat"] = int(time.time())
                            if b.get("status"): a["status"] = b["status"]
                            touch_session(a, event="beat")
                elif b.get("id"):
                    agents = [a for a in agents if a["id"] != b["id"]] + [b]
                else:
                    b["id"] = "agent-" + uuid.uuid4().hex[:6]
                    b.setdefault("status", "working"); b["last_heartbeat"] = int(time.time())
                    agents.append(b); touch_session(b, by="human")
                save("agents.json", agents); return self.send_json(agents)
            if u.path == "/api/tasks":
                tasks = load("tasks.json", [])
                if b.get("delete"): tasks = [t for t in tasks if t["id"] != b["delete"]]
                elif b.get("reopen"):
                    for t in tasks:
                        if t["id"] == b["reopen"]:
                            t["state"] = "doing"
                            t["updated"] = int(time.time())
                            log_event("task_reopen", f"{t['id']} -> doing")
                elif b.get("advance"):
                    for t in tasks:
                        if t["id"] == b["advance"]:
                            t["state"] = {"todo": "doing", "doing": "done", "done": "done"}[t["state"]]
                            if t["state"] == "doing": t["work_ticks"] = 0
                            else: t.pop("needs_human", None)
                            if b.get("result"): t["result"] = str(b["result"])[:500]
                            t["updated"] = int(time.time())
                            log_event("task_advance", f"{t['id']} -> {t['state']}")
                elif b.get("id"): tasks = [t for t in tasks if t["id"] != b["id"]] + [b]
                else:
                    b["id"] = "t-" + uuid.uuid4().hex[:4]; b.setdefault("state", "todo")
                    b["updated"] = int(time.time()); tasks.append(b)
                    log_event("task_created", f"{b['id']} {b.get('title', '')[:80]}")
                save("tasks.json", tasks); return self.send_json(tasks)
            if u.path == "/api/iterations":
                iters = load("iterations.json", [])
                if b.get("delete"): iters = [i for i in iters if i["id"] != b["delete"]]
                elif b.get("id"):
                    old = next((i for i in iters if i["id"] == b["id"]), {})
                    iters = [i for i in iters if i["id"] != b["id"]] + [b]
                    if b.get("state") == "released" and old.get("state") != "released":
                        _t = load("tasks.json", [])
                        n = stamp_release(_t, b["id"])
                        save("tasks.json", _t)
                        log_event("release", f"{b['id']} claimed {n} tasks")
                else:
                    b["id"] = "v0.%d.0" % (len(iters) + 1); b.setdefault("state", "planned")
                    b["ts"] = int(time.time()); iters.append(b)
                save("iterations.json", iters); log_event("iteration", b.get("id", "?")); return self.send_json(iters)
            if u.path == "/api/control/start":
                st = load("loop_state.json", {}); st["running"] = True; save("loop_state.json", st)
                log_event("loop", "started"); return self.send_json(st)
            if u.path == "/api/control/stop":
                st = load("loop_state.json", {}); st["running"] = False; save("loop_state.json", st)
                log_event("loop", "stopped"); return self.send_json(st)
            if u.path == "/api/loop/tick": return self.send_json(do_tick())
            if u.path == "/api/ops/restart":
                subprocess.Popen(["bash", os.path.join(ROOT, "bin", "restart-detached.sh"), str(os.getpid())],
                                 start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                log_event("ops", "restart requested"); return self.send_json({"restarting": True})
            if u.path == "/api/ops/daemon":
                if b.get("action", "start") == "stop":
                    try:
                        pid = int(open(p("loop.pid")).read().strip()); os.kill(pid, signal.SIGTERM)
                        log_event("ops", f"daemon {pid} stopped")
                    except Exception as e: log_event("ops", f"daemon stop: {e}")
                    try: os.remove(p("loop.pid"))
                    except Exception: pass
                    return self.send_json({"daemon": "stopped"})
                pr = subprocess.Popen(["bash", "bin/loop.sh", "daemon"], cwd=ROOT, start_new_session=True,
                                      stdout=open(os.path.join(ROOT, "loop-daemon.log"), "a"), stderr=subprocess.STDOUT)
                open(p("loop.pid"), "w").write(str(pr.pid))
                log_event("ops", f"daemon started {pr.pid}"); return self.send_json({"daemon": "started", "pid": pr.pid})
            if u.path == "/api/ops/file":
                name = b.get("name", "")
                if name not in ALLOW_FILES: return self.send_json({"error": "not editable"}, 403)
                content = b.get("content", "")
                if name == "server/app.py":
                    open(p("app_check.py"), "w").write(content)
                    r = subprocess.run([sys.executable, "-m", "py_compile", p("app_check.py")], capture_output=True, text=True)
                    if r.returncode != 0: return self.send_json({"error": "syntax: " + r.stderr[-500:]}, 400)
                if name == "needs.json":
                    try: json.loads(content)
                    except Exception as e: return self.send_json({"error": "bad json: " + str(e)}, 400)
                with open(os.path.join(ROOT, name), "w") as f: f.write(content)
                log_event("ops", f"saved {name}"); return self.send_json({"saved": name})
            if u.path == "/api/ops/snapshot":
                try: sid = snapshot_code(b.get("id", ""))
                except ValueError: return self.send_json({"error": "exists"}, 400)
                log_event("ops", f"snapshot {sid}"); return self.send_json({"snapshot": sid})
            if u.path == "/api/ops/restore":
                sid = b.get("id", ""); src = os.path.join(SNAP, sid)
                if not sid or not os.path.isdir(src): return self.send_json({"error": "no such snapshot"}, 404)
                for d in ("server", "public"):
                    shutil.rmtree(os.path.join(ROOT, d)); shutil.copytree(os.path.join(src, d), os.path.join(ROOT, d))
                for f in ("needs.json", "AGENTS.md"): shutil.copy2(os.path.join(src, f), os.path.join(ROOT, f))
                subprocess.Popen(["bash", os.path.join(ROOT, "bin", "restart-detached.sh"), str(os.getpid())],
                                 start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                log_event("ops", f"restored {sid}, restarting"); return self.send_json({"restored": sid, "restarting": True})
            return self.send_json({"error": "unknown endpoint"}, 404)

if __name__ == "__main__":
    s = settings()
    port = int(s.get("port", 8361)); bind = s.get("bind", "0.0.0.0")
    print(f"e086 company OS on {bind}:{port}", flush=True)
    ThreadingHTTPServer((bind, port), H).serve_forever()
