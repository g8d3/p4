"""e079 agent-cycles server: stdlib only. Board + web-configurable admin."""
import json, os, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(ROOT, "public")
NEEDS = os.path.join(ROOT, "needs.json")
OVER = os.path.join(ROOT, "data", "config.overrides.json")
SECRETS = os.path.join(ROOT, "data", "secrets.json")
TENANTS = os.path.join(ROOT, "data", "tenants.jsonl")
GOALS = os.path.join(ROOT, "data", "goals.jsonl")
LOOPLOG = os.path.join(ROOT, "data", "loop_log.jsonl")
CREDCACHE = os.path.join(ROOT, "data", "credits_cache.json")
METEREDCACHE = os.path.join(ROOT, "data", "metered_cache.json")
LEGCOSTS = os.path.join(ROOT, "data", "leg_costs.jsonl")
REFS = os.path.join(ROOT, "data", "refs.jsonl")
MANUAL = os.path.join(ROOT, "data", "last_manual_run")
METRICS = os.path.join(ROOT, "data", "metrics.jsonl")

def base_config():
    with open(NEEDS) as f: return json.load(f)

def load_config():
    cfg = base_config()
    try:
        if os.path.exists(OVER):
            with open(OVER) as f: cfg.update(json.load(f))
    except Exception: pass
    return cfg

CFG = load_config()
BOOT_TS = time.time()  # legs started after boot must bank >=1 idea to finish
DATA = os.path.join(ROOT, CFG.get("data_file", "data/cycles.jsonl"))
VERF = os.path.join(ROOT, CFG.get("version_file", "version.json"))

EDITABLE = ("site_name", "tagline", "domain_budget_yearly", "mor_provider",
            "margin_target", "niche_avg", "niche_stdev",
            "loop_interval_minutes", "loop_stale_minutes")

def read_cycles():
    if not os.path.exists(DATA): return []
    out = []
    with open(DATA) as f:
        for line in f:
            line = line.strip()
            if line:
                try: out.append(json.loads(line))
                except Exception: pass
    return out[-100:][::-1]

def read_version():
    try:
        with open(VERF) as f: return json.load(f)
    except Exception: return {"version": "v?", "notes": ""}

def read_lines(path):
    if not os.path.exists(path): return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try: out.append(json.loads(line))
                except Exception: pass
    return out

def metrics_state():
    rows = read_lines(METRICS)
    last = rows[-1] if rows else None
    out = {"entries": rows[-12:][::-1], "current": None}
    if last:
        rev = float(last.get("revenue", 0) or 0)
        ai = float(last.get("ai_cost", 0) or 0)
        infra = float(last.get("infra_cost", 0) or 0)
        margin = ((rev - ai - infra) / rev) if rev > 0 else None
        out["current"] = {"margin": margin, **last}
    return out

def credits_state():
    """Credit-aware: live Z.AI quota, server-side only, numbers out, key never leaves."""
    try:
        if os.path.exists(CREDCACHE):
            c = json.load(open(CREDCACHE))
            if time.time() - c.get("ts", 0) < 300 and c.get("data"):
                d = dict(c["data"]); d["cached"] = True; return d
    except Exception: pass
    key = os.environ.get("ZAI_API_KEY", "")
    if not key: return {"known": False, "reason": "no key on server"}
    try:
        import urllib.request
        req = urllib.request.Request("https://api.z.ai/api/monitor/usage/quota/limit",
                                     headers={"Authorization": key})
        q = json.load(urllib.request.urlopen(req, timeout=10))
        d = q.get("data", {})
        out = {"known": True, "level": d.get("level"), "cached": False}
        for lim in d.get("limits", []):
            if lim.get("type") == "TOKENS_LIMIT":
                out["tokens_pct"] = lim.get("percentage")
                out["tokens_reset"] = lim.get("nextResetTime")
            if lim.get("type") == "TIME_LIMIT":
                out["mcp_remaining"] = lim.get("remaining")
        with open(CREDCACHE, "w") as f: json.dump({"ts": time.time(), "data": out}, f)
        return out
    except Exception:
        return {"known": False, "reason": "quota fetch failed"}

def metered_state(days=30):
    """Metered cost: real per-model token usage from the plan history API.
    Server-side only, key never leaves. 5-min cache. Self-report is retired."""
    try:
        if os.path.exists(METEREDCACHE):
            c = json.load(open(METEREDCACHE))
            if (time.time() - c.get("ts", 0) < 300 and c.get("data")
                    and c["data"].get("window_days") == days):
                d = dict(c["data"]); d["cached"] = True; return d
    except Exception: pass
    key = os.environ.get("ZAI_API_KEY", "")
    if not key: return {"known": False, "reason": "no key on server"}
    try:
        import urllib.request, urllib.parse, datetime
        now = datetime.datetime.now()
        fmt = lambda dt: dt.strftime("%Y-%m-%d %H:%M:%S")
        q = urllib.parse.urlencode({
            "startTime": fmt(now - datetime.timedelta(days=days)),
            "endTime": fmt(now)})
        req = urllib.request.Request(
            "https://api.z.ai/api/monitor/usage/model-usage?" + q,
            headers={"Authorization": key})
        d = json.load(urllib.request.urlopen(req, timeout=15)).get("data", {})
        tot = d.get("totalUsage", {}) or {}
        models = [{"model": m.get("modelName"), "tokens": m.get("totalTokens", 0)}
                  for m in (tot.get("modelSummaryList") or [])]
        out = {"known": True, "window_days": days, "cached": False,
               "granularity": d.get("granularity", "hourly"),
               "total_tokens": tot.get("totalTokensUsage", 0),
               "total_calls": tot.get("totalModelCallCount", 0),
               "models": models}
        with open(METEREDCACHE, "w") as f: json.dump({"ts": time.time(), "data": out}, f)
        return out
    except Exception:
        return {"known": False, "reason": "history fetch failed"}

def public_config():
    cfg = load_config()
    mor_set = False
    try:
        if os.path.exists(SECRETS):
            mor_set = bool(json.load(open(SECRETS)).get("mor_api_key"))
    except Exception: pass
    return {k: cfg.get(k) for k in ("site_name", "tagline", "domain_budget_yearly",
            "mor_provider", "margin_target", "niche_avg", "niche_stdev",
            "loop_interval_minutes", "loop_stale_minutes",
            "port") } | {"mor_key_set": mor_set}

def check_admin(payload, headers):
    cfg = load_config()
    want = cfg.get("admin_token", "")
    got = payload.get("token") or headers.get("X-Admin-Token") or headers.get("x-admin-token")
    return bool(want) and got == want

MIME = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png"}

def share_png():
    """Server-rendered share card (1200x630) so link pastes unfurl rich.
    PIL if present, else stdlib flat PNG fallback. Text: site, version, notes."""
    v = read_version()
    cfg = load_config()
    site = (cfg.get("site_name") or "Agent Cycles")[:40]
    ver = (v.get("version") or "v?")[:12]
    notes = (v.get("notes") or "")[:140]
    W, H = 1200, 630
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        im = Image.new("RGB", (W, H), "#12161d")
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W - 1, H - 1], outline="#6ee7a8", width=6)
        d.rectangle([18, 18, W - 19, H - 19], outline="#2a3140", width=2)
        f_small = ImageFont.load_default(size=44)
        f_big = ImageFont.load_default(size=130)
        f_mid = ImageFont.load_default(size=40)
        d.text((70, 60), site, font=f_small, fill="#6ee7a8")
        d.text((70, 130), ver, font=f_big, fill="#eef1f6")
        y = 330
        for line in textwrap.wrap(notes, 44)[:4]:
            d.text((70, y), line, font=f_mid, fill="#9aa3b2")
            y += 52
        d.text((70, 552), "Ship one version per cycle.", font=f_small, fill="#6ee7a8")
        import io
        b = io.BytesIO()
        im.save(b, "PNG")
        return b.getvalue()
    except Exception:
        import struct, zlib
        raw = b"\x00" + bytes([18, 22, 29]) * W
        raw = raw * H
        def chunk(t, data):
            c = struct.pack(">I", len(data)) + t + data
            return c + struct.pack(">I", zlib.crc32(t + data) & 0xffffffff)
        ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send_json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        if p == "/api/cycles": return self.send_json(read_cycles())
        if p in ("/api/version", "/api/versions"):
            v = read_version()
            hist = [{"version": c["produced_version"], "notes": c.get("goal", ""),
                     "ts": c.get("finished_ts", c.get("started_ts", 0))}
                    for c in read_cycles()[::-1] if c.get("produced_version")]
            return self.send_json({"running": v, "history": hist})
        if p == "/api/config": return self.send_json(public_config())
        if p == "/api/metrics": return self.send_json(metrics_state())
        if p == "/api/tenants": return self.send_json(read_lines(TENANTS)[::-1][:100])
        if p == "/api/goals":
            rows = read_lines(GOALS)
            return self.send_json([r for r in rows if r.get("status") in ("queued", "active")][:20])
        if p == "/api/loop":
            stopped = os.path.exists(os.path.join(ROOT, "data", "STOP"))
            last = read_lines(LOOPLOG)[-1] if os.path.exists(LOOPLOG) else None
            iv = load_config().get("loop_interval_minutes", 30)
            age = (int(time.time()) - int(last.get("ts", 0)) // 1) if last else None
            try: age_min = (time.time() - int(last.get("ts", 0))) / 60 if last else None
            except Exception: age_min = None
            healthy = (age_min is not None and age_min < iv * 2.5) if not stopped else False
            install = "*/%d * * * * %s/bin/loop.sh >> %s/data/loop.log 2>&1" % (iv, ROOT, ROOT)
            cron_have = None
            try:
                import subprocess
                tab = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5).stdout
                for line in tab.splitlines():
                    if "e079-agent-cycles/bin/loop.sh" in line and line.strip() and not line.strip().startswith("#"):
                        cron_have = line.split()[:5]
                        cron_have = " ".join(cron_have)
                        break
            except Exception: pass
            queued = sum(1 for r in read_lines(GOALS) if r.get("status") == "queued")
            allc = read_cycles()
            traj = [{"id": c["id"], "status": c["status"],
                     "v": c.get("produced_version"),
                     "age_min": round((time.time() - int(c.get("started_ts", time.time()))) / 60, 1)}
                    for c in allc[:10]]
            streak = 0
            for c in allc:
                if c.get("status") == "void": streak += 1
                else: break
            alert = None
            if streak >= 2:
                alert = f"void streak {streak} — workers dying silently, check autopsy + fuel"
            elif queued == 0 and not any(c.get("status") == "running" for c in allc):
                alert = "queue drained — chain parked, nothing scheduled until ideas banked"
            run = [c for c in allc if c.get("status") == "running"]
            if run and (time.time() - int(run[0].get("started_ts", time.time()))) > 45 * 60:
                alert = f"lane stuck: {run[0]['id']} over 45min with no finish"
            turbo = os.path.exists(os.path.join(ROOT, "data", "TURBO"))
            thinker = os.path.exists(os.path.join(ROOT, "data", "THINKER"))
            thinker_install = "0 * * * * %s/bin/thinker.sh >> %s/data/thinker.log 2>&1" % (ROOT, ROOT)
            thinker_cron = None
            try:
                for line in tab.splitlines():
                    if "e079-agent-cycles/bin/thinker.sh" in line and line.strip() and not line.strip().startswith("#"):
                        thinker_cron = " ".join(line.split()[:5])
                        break
            except Exception: pass
            return self.send_json({"stopped": stopped, "last_leg": last,
                                    "last_leg_age_min": round(age_min, 1) if age_min is not None else None,
                                    "healthy": healthy, "install_line": install,
                                    "cron_have": cron_have, "turbo": turbo,
                                    "thinker": thinker, "thinker_cron": thinker_cron,
                                    "trajectory": traj, "void_streak": streak, "alert": alert,
                                    "thinker_install": thinker_install,
                                    "queue_depth": queued, "interval_min": iv})
        if p == "/api/credits": return self.send_json(credits_state())
        if p == "/api/leg":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            cid = (qs.get("cycle") or [""])[0]
            cyc = [c for c in read_cycles() if c.get("id") == cid]
            if not cyc: return self.send_json({"error": "no such cycle"}, 404)
            c = cyc[0]
            if c.get("status") == "done":
                return self.send_json({"cycle": cid, "verdict": "SHIPPED",
                                        "detail": c.get("produced_version", "?"), "goal": c.get("goal", "")})
            if c.get("status") == "void":
                return self.send_json({"cycle": cid, "verdict": "VOID",
                                        "detail": (c.get("void_reason") or "?"), "goal": c.get("goal", "")})
            try: st = json.load(open(os.path.join(PUBLIC, "legs", cid + ".status.json")))
            except Exception: st = None
            try: w = json.load(open(os.path.join(ROOT, "data", "workers.json"))).get("legs", {}).get(cid)
            except Exception: w = None
            if not st:
                return self.send_json({"cycle": cid, "verdict": "UNKNOWN",
                                        "detail": "leg started before streaming — no heartbeat exists",
                                        "goal": c.get("goal", "")})
            now = time.time()
            sa = now - int(st.get("updated_ts", st.get("started_ts", now)))
            try: la = now - os.path.getmtime(os.path.join(PUBLIC, "legs", cid + ".log"))
            except Exception: la = None
            alive = bool(w and w.get("alive"))
            silent = min([a for a in (sa, la) if a is not None] or [sa])
            if (la is not None and la < 120) or sa < 120:
                v, d = "WORKING", "output %ds ago" % int(la if la is not None else sa)
            elif not alive:
                left = max(0, 900 - int(silent))
                v, d = ("DEAD", "no worker; keeper voids in ~%ds" % left) if silent < 900 else ("DEAD", "no worker; keeper void due")
            elif silent > 300:
                v, d = "STALLED", "worker alive but quiet %ds" % int(silent)
            else:
                v, d = "QUIET", "quiet %ds, within tolerance" % int(silent)
            return self.send_json({"cycle": cid, "verdict": v, "detail": d,
                                    "started_ts": int(c.get("started_ts", now)),
                                    "goal": st.get("goal", ""), "why": st.get("why", ""),
                                    "phase": st.get("phase", ""), "note": st.get("note", ""),
                                    "silent_s": int(silent), "alive": alive})
        if p == "/api/refs":
            counts = {}
            for r in read_lines(REFS):
                c = (r.get("code") or "?")[:40]
                counts[c] = counts.get(c, 0) + 1
            shipped = {}
            for c in read_cycles():
                if c.get("produced_version") and c.get("ref"):
                    rc = (c.get("ref") or "?")[:40]
                    shipped[rc] = shipped.get(rc, 0) + 1
                    counts.setdefault(rc, 0)
            top = sorted(counts.items(), key=lambda kv: (shipped.get(kv[0], 0), kv[1]), reverse=True)[:20]
            return self.send_json([{"code": c, "hits": n, "shipped": shipped.get(c, 0)} for c, n in top])
        if p == "/api/legs/metered":
            try:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                days = max(1, min(90, int((qs.get("days") or ["30"])[0])))
            except Exception: days = 30
            return self.send_json(metered_state(days))
        if p == "/share.png":
            try:
                b = share_png()
            except Exception:
                self.send_response(500); self.end_headers(); return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "public, max-age=60")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        if p == "/api/legs/costs":
            rows = read_lines(LEGCOSTS)
            return self.send_json({"entries": rows[::-1][:50],
                                    "total_usd": round(sum(float(r.get("cost_usd", 0) or 0) for r in rows), 4)})
        if p in ("/", "/index.html"): p = "/index.html"
        fp = os.path.join(PUBLIC, p.lstrip("/"))
        if os.path.isfile(fp):
            ext = os.path.splitext(fp)[1]
            with open(fp, "rb") as f: b = f.read()
            if os.path.basename(fp) == "index.html":
                try:
                    v = read_version()
                    baked = "%s \u2014 %s" % (v.get("version", "v?"), v.get("notes", ""))
                    b = b.replace(b"__BAKED_VERSION__", baked.encode())
                except Exception: pass
            self.send_response(200)
            self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        self.send_response(404); self.end_headers()
    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        n = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(n) if n else b"{}"
        try: payload = json.loads(body or b"{}")
        except Exception: payload = {}
        h = {k.lower(): v for k, v in dict(self.headers).items()}
        if p == "/api/cycle/start": return self.start_cycle(payload)
        if p == "/api/cycle/void": return self.void_cycle(payload, h)
        if p == "/api/cycle/finish": return self.finish_cycle(payload)
        if p == "/api/admin/config":
            if not check_admin(payload, h): return self.send_json({"error": "bad admin token"}, 403)
            over = {}
            try:
                if os.path.exists(OVER): over = json.load(open(OVER))
            except Exception: over = {}
            for k in EDITABLE:
                if k in payload: over[k] = payload[k]
            os.makedirs(os.path.dirname(OVER), exist_ok=True)
            with open(OVER, "w") as f: json.dump(over, f, indent=2)
            if payload.get("mor_api_key"):
                sec = {}
                try:
                    if os.path.exists(SECRETS): sec = json.load(open(SECRETS))
                except Exception: sec = {}
                sec["mor_api_key"] = payload["mor_api_key"]
                with open(SECRETS, "w") as f: json.dump(sec, f)
                try: os.chmod(SECRETS, 0o600)
                except Exception: pass
            global CFG
            CFG = load_config()
            return self.send_json(public_config())
        if p == "/api/admin/reload":
            CFG = load_config()
            return self.send_json({"ok": True})
        if p == "/api/goals/add":
            if not check_admin(payload, h): return self.send_json({"error": "bad admin token"}, 403)
            g = (payload.get("goal") or "").strip()[:200]
            if not g: return self.send_json({"error": "goal required"}, 400)
            w = (payload.get("why") or "").strip()[:300]
            if len(w) < 10:
                return self.send_json({"error": "why required (>=10 chars): what breaks if this never ships?"}, 400)
            # Guarantee: every bank is credited. Omitted "cycle" key = credit the
            # running cycle (a thinking leg banking). Explicit null = no credit.
            banked_by = payload.get("cycle", "__auto__")
            if banked_by == "__auto__":
                banked_by = None
                try:
                    live = [c for c in read_cycles() if c.get("status") == "running"]
                    if len(live) == 1: banked_by = live[0]["id"]
                except Exception: pass
            with open(GOALS, "a") as f:
                f.write(json.dumps({"goal": g, "why": w, "status": "queued",
                                    "ts": int(time.time()), "banked_by": banked_by}) + "\n")
            return self.send_json({"ok": True, "banked_by": banked_by})
        if p == "/api/admin/stop":
            if not check_admin(payload, h): return self.send_json({"error": "bad admin token"}, 403)
            sp = os.path.join(ROOT, "data", "STOP")
            if payload.get("stopped"):
                open(sp, "w").write("stopped %d" % int(time.time()))
            elif os.path.exists(sp):
                os.remove(sp)
            return self.send_json({"stopped": os.path.exists(sp)})
        if p == "/api/legs/log":
            local = self.client_address[0] in ("127.0.0.1", "::1")
            if not local and not check_admin(payload, h):
                return self.send_json({"error": "bad admin token"}, 403)
            try: cost = float(payload.get("cost_usd", 0))
            except (TypeError, ValueError):
                return self.send_json({"error": "cost_usd must be a number"}, 400)
            e = {"ts": int(time.time()), "model": (payload.get("model") or "?")[:60],
                 "cost_usd": cost, "notes": (payload.get("notes") or "")[:200]}
            with open(LEGCOSTS, "a") as f: f.write(json.dumps(e) + "\n")
            return self.send_json({"ok": True})
        if p == "/api/ref":
            code = (payload.get("code") or "").strip()[:40] or "anon"
            with open(REFS, "a") as f:
                f.write(json.dumps({"ts": int(time.time()), "code": code}) + "\n")
            return self.send_json({"ok": True})
        if p == "/api/loop/run":
            # Run-now: bounded + safe (one-at-a-time lane), so any board user may
            # trigger it. 60s cooldown against button spam; loop.sh does the rest.
            now = time.time()
            try: lastm = float(open(MANUAL).read().strip())
            except Exception: lastm = 0
            if now - lastm < 60:
                return self.send_json({"error": "cooldown", "retry_in_s": int(60 - (now - lastm))}, 429)
            with open(MANUAL, "w") as f: f.write(str(now))
            import subprocess
            subprocess.Popen(["bash", os.path.join(ROOT, "bin", "loop.sh")],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return self.send_json({"accepted": True})
        if p == "/api/admin/turbo":
            if not check_admin(payload, h): return self.send_json({"error": "bad admin token"}, 403)
            sp = os.path.join(ROOT, "data", "TURBO")
            if payload.get("turbo"):
                open(sp, "w").write("turbo %d" % int(time.time()))
            elif os.path.exists(sp):
                os.remove(sp)
            return self.send_json({"turbo": os.path.exists(sp)})
        if p == "/api/admin/thinker":
            if not check_admin(payload, h): return self.send_json({"error": "bad admin token"}, 403)
            sp = os.path.join(ROOT, "data", "THINKER")
            if payload.get("thinker"):
                open(sp, "w").write("armed %d" % int(time.time()))
            elif os.path.exists(sp):
                os.remove(sp)
            return self.send_json({"thinker": os.path.exists(sp)})
        if p == "/api/tenants/add":
            if not check_admin(payload, h): return self.send_json({"error": "bad admin token"}, 403)
            name = (payload.get("name") or "").strip()[:80]
            if not name: return self.send_json({"error": "name required"}, 400)
            rows = read_lines(TENANTS)
            t = {"id": "t%03d" % (len(rows) + 1), "name": name,
                 "plan": (payload.get("plan") or "free")[:20], "status": "active",
                 "ts": int(time.time())}
            with open(TENANTS, "a") as f: f.write(json.dumps(t) + "\n")
            return self.send_json(t)
        if p == "/api/metrics/add":
            if not check_admin(payload, h): return self.send_json({"error": "bad admin token"}, 403)
            try:
                e = {"ts": int(time.time()),
                     "revenue": float(payload.get("revenue", 0)),
                     "ai_cost": float(payload.get("ai_cost", 0)),
                     "infra_cost": float(payload.get("infra_cost", 0)),
                     "niche_avg": float(payload.get("niche_avg", load_config().get("niche_avg", 0.25)))}
            except (TypeError, ValueError):
                return self.send_json({"error": "numbers required"}, 400)
            with open(METRICS, "a") as f: f.write(json.dumps(e) + "\n")
            return self.send_json(metrics_state())
        self.send_json({"error": "unknown"}, 404)
    def start_cycle(self, payload):
        goal = (payload.get("goal") or "next version").strip()[:200] or "next version"
        why = (payload.get("why") or "").strip()[:300] or None
        tenant = (payload.get("tenant") or "").strip()[:20] or None
        ref = (payload.get("ref") or "").strip()[:40] or None
        cycles = read_cycles()
        for c in cycles:
            if c.get("status") == "running":
                return self.send_json({"error": "one cycle at a time", "running": c}, 409)
        try:
            with open(DATA) as f: n = sum(1 for _ in f if _.strip())
        except Exception: n = 0
        entry = {"id": "c%03d" % (n + 1), "goal": goal, "why": why, "status": "running",
                 "started_ts": int(time.time()), "produced_version": None,
                 "tenant": tenant, "ref": ref}
        os.makedirs(os.path.dirname(DATA), exist_ok=True)
        with open(DATA, "a") as f: f.write(json.dumps(entry) + "\n")
        return self.send_json(entry)
    def void_cycle(self, payload, h):
        if not check_admin(payload, h): return self.send_json({"error": "bad admin token"}, 403)
        cid = payload.get("id")
        reason = (payload.get("reason") or "void").strip()[:200]
        if not cid: return self.send_json({"error": "id required"}, 400)
        lines = []
        if os.path.exists(DATA):
            with open(DATA) as f: lines = [l for l in f if l.strip()]
        out, found = [], None
        for l in lines:
            try: c = json.loads(l)
            except Exception: continue
            if c.get("id") == cid and c.get("status") == "running":
                c["status"] = "void"
                c["finished_ts"] = int(time.time())
                c["void_reason"] = reason
                found = c
            out.append(c)
        if not found: return self.send_json({"error": "no running cycle " + str(cid)}, 404)
        with open(DATA, "w") as f:
            for c in out: f.write(json.dumps(c) + "\n")
        try:
            goals = read_lines(GOALS)
            changed = False
            for g in goals:
                if g.get("status") == "active" and g.get("cycle") == cid:
                    g["status"] = "done"; g["void"] = True; changed = True
            if changed:
                with open(GOALS, "w") as f:
                    for g in goals: f.write(json.dumps(g) + "\n")
        except Exception: pass
        return self.send_json(found)
    def finish_cycle(self, payload):
        cid = payload.get("id")
        notes = (payload.get("notes") or "").strip()[:300]
        if not cid: return self.send_json({"error": "id required"}, 400)
        # Guarantee (owner law, enforced): a cycle started after boot finishes
        # only if it banked >=1 idea with a why. No bank, no version. No exceptions.
        try:
            with open(DATA) as f:
                cur = [json.loads(l) for l in f if l.strip()]
            me = [c for c in cur if c.get("id") == cid and c.get("status") == "running"]
            if me and int(me[0].get("started_ts", 0)) > BOOT_TS:
                banked = [g for g in read_lines(GOALS) if g.get("banked_by") == cid]
                if not banked:
                    return self.send_json({"error": "bank one idea first (POST /api/goals/add with goal+why); the queue must grow every cycle"}, 409)
        except Exception as e:
            if "bank one idea" in str(e): raise
            pass
        lines = []
        if os.path.exists(DATA):
            with open(DATA) as f: lines = [l for l in f if l.strip()]
        out, found = [], None
        for l in lines:
            try: c = json.loads(l)
            except Exception: continue
            if c.get("id") == cid and c.get("status") == "running":
                v = read_version()
                try: num = int(v.get("version", "v1").lstrip("v").split(".")[0])
                except Exception: num = 1
                newv = "v%d" % (num + 1)
                c["status"] = "done"
                c["finished_ts"] = int(time.time())
                c["produced_version"] = newv
                if notes: c["goal"] = c.get("goal", "") + " | " + notes
                with open(VERF, "w") as f: json.dump({"version": newv, "notes": notes or c.get("goal", "")}, f)
                found = c
            out.append(c)
        if not found: return self.send_json({"error": "no running cycle " + str(cid)}, 404)
        with open(DATA, "w") as f:
            for c in out: f.write(json.dumps(c) + "\n")
        return self.send_json(found)

if __name__ == "__main__":
    port = int(CFG.get("port", 8339))
    bind = CFG.get("bind", "0.0.0.0")
    print(f"e079 serving {bind}:{port} root={ROOT}", flush=True)
    ThreadingHTTPServer((bind, port), H).serve_forever()
