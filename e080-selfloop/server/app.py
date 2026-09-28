#!/usr/bin/env python3
"""Selfloop server — stdlib only. Serves public/ + /api/*."""
import json, os, time, datetime, urllib.parse

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEEDS = os.path.join(DIR, "needs.json")
VERSION_F = os.path.join(DIR, "version.json")
DATA = os.path.join(DIR, "data")
PUB = os.path.join(DIR, "public")

def load(p, d):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return d

def load_lines(p):
    if not os.path.exists(p): return []
    out = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                try: out.append(json.loads(line))
                except Exception: pass
    return out

def append_line(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(obj) + "\n")

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

def cfg():
    return load(NEEDS, {})

def version():
    return load(VERSION_F, {"version": "v1", "notes": "", "updated_at": ""})

def cycles():
    return load_lines(os.path.join(DATA, "cycles.jsonl"))

def running_cycle():
    for c in reversed(cycles()):
        if c.get("status") == "running": return c
    return None

def goals():
    return load_lines(os.path.join(DATA, "goals.jsonl"))

def open_goals():
    done_ids = set()
    out = []
    for g in goals():
        if g.get("done"): done_ids.add(g.get("id"))
    for g in goals():
        if not g.get("done") and g.get("id") not in done_ids and g.get("text"):
            out.append(g)
    # dedupe by text, keep first
    seen, uniq = set(), []
    for g in out:
        if g["text"] not in seen:
            seen.add(g["text"]); uniq.append(g)
    return uniq

def usage():
    return load_lines(os.path.join(DATA, "usage.jsonl"))

def fixes():
    return load_lines(os.path.join(DATA, "fixes.jsonl"))

def heartbeat():
    return load(os.path.join(DATA, "heartbeat.json"), {})

def bump_version(notes):
    v = version()
    n = 1
    try: n = int(str(v.get("version", "v1")).lstrip("v")) + 1
    except Exception: n = 1
    nv = {"version": f"v{n}", "notes": notes, "updated_at": now_iso()}
    with open(VERSION_F, "w") as f: json.dump(nv, f)
    return nv

def usage_summary(since_days=None):
    c = cfg()
    if since_days is None: since_days = c.get("since_default_days", 30)
    cutoff = time.time() - since_days * 86400
    tot_in = tot_out = 0
    tot_cost = 0.0
    models, endpoints = set(), set()
    all_in = all_out = 0
    all_cost = 0.0
    for u in usage():
        ti = int(u.get("tokens_in", 0)); to = int(u.get("tokens_out", 0))
        cost = float(u.get("cost", (ti + to) / 1000.0 * c.get("cost_per_1k_tokens", 0.002)))
        all_in += ti; all_out += to; all_cost += cost
        if u.get("model"): models.add(u["model"])
        if u.get("endpoint"): endpoints.add(u["endpoint"])
        try:
            ts = datetime.datetime.fromisoformat(str(u.get("at", "")).replace("Z", "+00:00")).timestamp()
        except Exception: ts = 0
        if ts >= cutoff:
            tot_in += ti; tot_out += to; tot_cost += cost
    if not models: models.add(c.get("default_model", "glm-4.6"))
    if not endpoints: endpoints.add(c.get("default_endpoint", "zai-coding-plan"))
    budget = float(c.get("credits_total", 50))
    return {
        "tokens_in": all_in, "tokens_out": all_out,
        "tokens_total": all_in + all_out, "cost_total": round(all_cost, 4),
        "since_days": since_days, "since_tokens": tot_in + tot_out,
        "since_cost": round(tot_cost, 4),
        "credits_total": budget, "credits_left": round(budget - all_cost, 4),
        "models": sorted(models), "endpoints": sorted(endpoints),
        "entries": len(usage()),
    }

def age_minutes(iso):
    try:
        ts = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp()
        return (time.time() - ts) / 60.0
    except Exception: return 1e9

def health():
    c = cfg()
    hb = heartbeat()
    hb_age = age_minutes(hb.get("at")) if hb.get("at") else 1e9
    rc = running_cycle()
    rc_age = age_minutes(rc.get("started_at")) if rc else 0
    v = version()
    v_age = age_minutes(v.get("updated_at")) if v.get("updated_at") else 1e9
    stale_min = float(c.get("loop_stale_minutes", 60))
    stuck_min = float(c.get("stuck_after_minutes", 120))
    hb_stale = float(c.get("heartbeat_stale_minutes", 10))
    reasons = []
    if rc and rc_age > stale_min:
        reasons.append(f"running cycle {rc.get('id')} stale ({rc_age:.0f}m > {stale_min:.0f}m)")
    if v_age > stuck_min and not rc:
        reasons.append(f"no version bump for {v_age:.0f}m (> {stuck_min:.0f}m)")
    if hb_age > hb_stale:
        reasons.append(f"loop heartbeat stale ({hb_age:.0f}m > {hb_stale:.0f}m)")
    return {
        "alive": True, "stuck": len(reasons) > 0, "reasons": reasons,
        "heartbeat_age_minutes": round(hb_age, 1) if hb_age < 1e8 else None,
        "running_cycle": rc, "running_age_minutes": round(rc_age, 1) if rc else None,
        "version_age_minutes": round(v_age, 1) if v_age < 1e8 else None,
    }

def simplicity():
    idx = os.path.join(PUB, "index.html")
    try: size = os.path.getsize(idx)
    except Exception: size = 0
    try:
        with open(idx) as f: html = f.read()
        sections = html.count("<section")
        buttons = html.count("<button")
    except Exception: sections = buttons = 0
    grade = "A" if size < 30000 and sections <= 8 else "B" if size < 60000 else "C"
    return {"html_bytes": size, "sections": sections, "actions": buttons,
            "grade": grade,
            "verdict": f"Grade {grade}: one page, {sections} sections, {buttons} actions, {size//1024}KB. " +
            ("As simple as it could be — one page does it." if grade == "A" else "Could be simpler — propose a cut as next goal.")}

def answer_questions():
    c = cfg(); v = version(); h = health(); u = usage_summary()
    og = open_goals(); cs = cycles(); fs = fixes()
    hb = heartbeat()
    hb_txt = f"{h['heartbeat_age_minutes']}m ago" if h["heartbeat_age_minutes"] is not None else "never — loop hasn't beaten yet"
    stuck_txt = ("YES — " + "; ".join(h["reasons"]) if h["stuck"]
                 else "No. Versions shipping, heartbeat fresh.")
    nxt = og[0]["text"] if og else "No open goals — add one. The loop never idles."
    past = f"{len([x for x in cs if x.get('status')=='done'])} versions shipped, {len(fs)} stuck-recoveries."
    present = f"{v['version']} alive, heartbeat {hb_txt}."
    future = f"{len(og)} open goals. Next: {nxt}"
    s = simplicity()
    Q = [
        ("Is the app working?",
         f"Yes — server alive, {present}" if h["heartbeat_age_minutes"] is not None and (h["heartbeat_age_minutes"] or 0) < 30 else f"Server serves, but loop heartbeat is {hb_txt}. That itself is shown here — no need to ask.",
         "health+heartbeat"),
        ("Is development stuck?",
         stuck_txt + (f" Last fix: {fs[-1]['fix']}" if fs else ""),
         "health+cycles"),
        ("How many tokens is the app using?",
         f"{u['tokens_total']} total ({u['tokens_in']} in / {u['tokens_out']} out) across {u['entries']} ledger entries.",
         "usage.jsonl"),
        (f"How many credits used (last {u['since_days']}d)?",
         f"${u['since_cost']} in last {u['since_days']}d; ${u['cost_total']} all-time.",
         "usage.jsonl"),
        ("How many credits are left?",
         f"${u['credits_left']} left of ${u['credits_total']} budget.",
         "needs.json budget − usage"),
        ("Which endpoints and models is the app using?",
         f"Models: {', '.join(u['models'])}. Endpoints: {', '.join(u['endpoints'])}.",
         "usage.jsonl + needs.json"),
        ("Is the UI as simple as it could be?",
         s["verdict"], "index.html metrics"),
        ("What is the past / present / future?",
         f"Past: {past} Present: {present} Future: {future}", "cycles+goals+version"),
        ("Why / What / How?",
         f"Why: {c.get('why','')} What: {c.get('what','')} How: {c.get('how','')}", "needs.json"),
        ("What ships next?",
         nxt, "goals.jsonl"),
    ]
    at = now_iso()
    ans = [{"q": q, "a": a, "src": src, "at": at} for q, a, src in Q]
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "answers.json"), "w") as f:
        json.dump({"at": at, "answers": ans}, f)
    append_line(os.path.join(DATA, "answers.jsonl"), {"at": at, "count": len(ans)})
    return {"at": at, "answers": ans}

def latest_answers():
    d = load(os.path.join(DATA, "answers.json"), {})
    if d.get("answers"): return d
    return answer_questions()

def state():
    c = cfg(); v = version()
    return {"site": {"name": c.get("site_name"), "tagline": c.get("tagline")},
            "version": v, "health": health(), "usage": usage_summary(),
            "why": c.get("why"), "what": c.get("what"), "how": c.get("how"),
            "answers": latest_answers(),
            "cycles": cycles()[-20:], "goals": open_goals()[:20],
            "fixes": fixes()[-10:], "all_cycles": len(cycles())}

# ---- HTTP ----
MIME = {".html": "text/html", ".js": "text/javascript", ".css": "text/css",
        ".svg": "image/svg+xml", ".json": "application/json", ".png": "image/png"}

def send(h, code, body, ctype="application/json"):
    b = body if isinstance(body, bytes) else body.encode()
    h.send_response(code)
    h.send_header("Content-Type", ctype + "; charset=utf-8")
    h.send_header("Content-Length", str(len(b)))
    h.send_header("Access-Control-Allow-Origin", "*")
    h.end_headers()
    h.wfile.write(b)

def read_json(h):
    try:
        n = int(h.headers.get("Content-Length", 0) or 0)
        if n <= 0: return {}
        return json.loads(h.rfile.read(n) or b"{}")
    except Exception: return {}

def fix_stuck(reason_override=None):
    h = health()
    if not h["stuck"] and not reason_override:
        return {"fixed": False, "msg": "not stuck"}
    reasons = [reason_override] if reason_override else h["reasons"]
    rc = running_cycle()
    fix_notes = []
    if rc:
        rc["status"] = "done"
        rc["finished_at"] = now_iso()
        rc["notes"] = (rc.get("notes") or rc.get("goal", "")) + " [stuck-recovered]"
        # rewrite cycles file: replace running entry
        cs = cycles()
        for i in range(len(cs) - 1, -1, -1):
            if cs[i].get("id") == rc.get("id") and cs[i].get("status") == "running":
                cs[i] = rc; break
        with open(os.path.join(DATA, "cycles.jsonl"), "w") as f:
            for c in cs: f.write(json.dumps(c) + "\n")
        nv = bump_version(f"unstuck: recovered stale {rc.get('id')}")
        fix_notes.append(f"finished stale {rc.get('id')}, shipped {nv['version']}")
    og = open_goals()
    nxt = og[0]["text"] if og else "Keep board breathing: smallest visible polish"
    # start fresh cycle with smallest goal
    cs = cycles()
    cid = f"c{len(cs)+1:03d}"
    append_line(os.path.join(DATA, "cycles.jsonl"),
                {"id": cid, "goal": nxt, "status": "running",
                 "started_at": now_iso(), "from_version": version()["version"]})
    fix_notes.append(f"started {cid}: {nxt}")
    rec = {"at": now_iso(), "reason": "; ".join(reasons), "fix": "; ".join(fix_notes)}
    append_line(os.path.join(DATA, "fixes.jsonl"), rec)
    answer_questions()
    return {"fixed": True, **rec}

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if p in ("/api/version",): return send(self, 200, json.dumps(version()))
        if p in ("/api/state",): return send(self, 200, json.dumps(state()))
        if p in ("/api/health",): return send(self, 200, json.dumps(health()))
        if p in ("/api/cycles",): return send(self, 200, json.dumps(cycles()))
        if p in ("/api/goals",): return send(self, 200, json.dumps(open_goals()))
        if p in ("/api/fixes",): return send(self, 200, json.dumps(fixes()))
        if p in ("/api/questions", "/api/answers"): return send(self, 200, json.dumps(latest_answers()))
        if p in ("/api/usage",):
            d = int(q.get("since_days", [0])[0] or 0)
            return send(self, 200, json.dumps(usage_summary(d if d else None)))
        if p in ("/api/config",):
            c = cfg(); return send(self, 200, json.dumps(c))
        # static
        rel = p[1:] if p != "/" else "index.html"
        fp = os.path.join(PUB, rel)
        if os.path.isdir(fp): fp = os.path.join(fp, "index.html")
        if os.path.exists(fp):
            ext = os.path.splitext(fp)[1]
            with open(fp, "rb") as f: data = f.read()
            return send(self, 200, data, MIME.get(ext, "text/plain"))
        return send(self, 404, json.dumps({"error": "not found"}))
    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        b = read_json(self)
        if p == "/api/heartbeat":
            rec = {"at": now_iso(), "by": b.get("by", "loop")}
            with open(os.path.join(DATA, "heartbeat.json"), "w") as f: json.dump(rec, f)
            return send(self, 200, json.dumps(rec))
        if p == "/api/ask":
            return send(self, 200, json.dumps(answer_questions()))
        if p == "/api/fix":
            return send(self, 200, json.dumps(fix_stuck(b.get("reason"))))
        if p == "/api/cycle/start":
            if running_cycle(): return send(self, 409, json.dumps({"error": "one running cycle max"}))
            goal = (b.get("goal") or "").strip()
            if not goal:
                og = open_goals()
                goal = og[0]["text"] if og else "Keep board breathing"
            cs = cycles(); cid = f"c{len(cs)+1:03d}"
            rec = {"id": cid, "goal": goal, "status": "running",
                   "started_at": now_iso(), "from_version": version()["version"]}
            append_line(os.path.join(DATA, "cycles.jsonl"), rec)
            return send(self, 200, json.dumps(rec))
        if p == "/api/cycle/finish":
            rc = running_cycle()
            if not rc: return send(self, 409, json.dumps({"error": "no running cycle"}))
            notes = (b.get("notes") or rc.get("goal") or "ship").strip()
            nv = bump_version(notes)
            cs = cycles()
            for i in range(len(cs) - 1, -1, -1):
                if cs[i].get("id") == rc.get("id") and cs[i].get("status") == "running":
                    cs[i]["status"] = "done"; cs[i]["finished_at"] = now_iso()
                    cs[i]["notes"] = notes; cs[i]["to_version"] = nv["version"]
                    break
            with open(os.path.join(DATA, "cycles.jsonl"), "w") as f:
                for c in cs: f.write(json.dumps(c) + "\n")
            # mark goal done if it matches
            gs = goals()
            changed = False
            for g in gs:
                if not g.get("done") and g.get("text", "").strip() == rc.get("goal", "").strip():
                    g["done"] = True; changed = True; break
            if changed:
                with open(os.path.join(DATA, "goals.jsonl"), "w") as f:
                    for g in gs: f.write(json.dumps(g) + "\n")
            answer_questions()
            return send(self, 200, json.dumps({"version": nv, "cycle": rc.get("id")}))
        if p == "/api/goals/add":
            t = (b.get("text") or "").strip()
            if not t: return send(self, 400, json.dumps({"error": "empty goal"}))
            gs = goals()
            rec = {"id": f"g{len(gs)+1:03d}", "text": t, "added_at": now_iso()}
            append_line(os.path.join(DATA, "goals.jsonl"), rec)
            return send(self, 200, json.dumps(rec))
        if p == "/api/usage/add":
            c = cfg()
            ti = int(b.get("tokens_in", 0)); to = int(b.get("tokens_out", 0))
            cost = float(b.get("cost", (ti + to) / 1000.0 * c.get("cost_per_1k_tokens", 0.002)))
            rec = {"at": now_iso(), "model": b.get("model", c.get("default_model")),
                   "endpoint": b.get("endpoint", c.get("default_endpoint")),
                   "tokens_in": ti, "tokens_out": to, "cost": round(cost, 4),
                   "note": b.get("note", "")}
            append_line(os.path.join(DATA, "usage.jsonl"), rec)
            return send(self, 200, json.dumps(rec))
        if p == "/api/admin/reload":
            return send(self, 200, json.dumps({"ok": True, "config": cfg()}))
        return send(self, 404, json.dumps({"error": "not found"}))

if __name__ == "__main__":
    c = cfg()
    port = int(c.get("port", 8340)); bind = c.get("bind", "0.0.0.0")
    os.makedirs(DATA, exist_ok=True)
    print(f"selfloop on {bind}:{port}", flush=True)
    ThreadingHTTPServer((bind, port), H).serve_forever()
