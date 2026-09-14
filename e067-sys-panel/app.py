#!/usr/bin/env python3
"""e067 sys-panel — ports/apps + cron + systemd services manager. Port 8326."""
import collections
import concurrent.futures
import html
import json
import os
import pwd
import re
import signal
import sqlite3
import subprocess
import threading
import time
import urllib.request

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "ops.db")
PORT = int(os.environ.get("E067_PORT", "8326"))

app = FastAPI(title="sys-panel")


# ---------------------------------------------------------- fast cache ---
# Short-TTL in-memory cache so repeated tab switches feel instant.
# Mutations and the live watcher invalidate per domain.
_CACHE = {}
_CACHE_LOCK = threading.Lock()


def cache_get(key):
    with _CACHE_LOCK:
        e = _CACHE.get(key)
        if e and e["exp"] > time.time():
            return e["val"]
    return None


def cache_set(key, val, ttl):
    with _CACHE_LOCK:
        _CACHE[key] = {"exp": time.time() + ttl, "val": val}


def cache_invalidate(*prefixes):
    with _CACHE_LOCK:
        for k in [k for k in _CACHE if k[0] in prefixes]:
            del _CACHE[k]


# ---------------------------------------------------------- live watch ---
# Fingerprints of system state; versions bump on change, pushed via SSE.
_versions = {"ports": 0, "cron": 0, "services": 0}
_ver_lock = threading.Lock()
_changes = collections.deque(maxlen=20)


def _note_change(kind, msg):
    with _ver_lock:
        _versions[kind] += 1
        _changes.append({"t": int(time.time()), "kind": kind, "msg": msg})
    cache_invalidate(kind)


def _fp_ports():
    try:
        p = run(["ss", "-tlnp"])
        items = set()
        for line in p.stdout.splitlines():
            m = re.search(r"(?:^|\s)(?:\d+\.\d+\.\d+\.\d+|\[::\]|\*):(\d+)\s", line)
            if m:
                pm = re.search(r"pid=(\d+)", line)
                items.add((int(m.group(1)), int(pm.group(1)) if pm else 0))
        return items
    except Exception:
        return set()


def _fp_cron():
    try:
        return hash(user_crontab())
    except Exception:
        return 0


def _fp_services():
    try:
        out = []
        for u in (False, True):
            cmd = (["systemctl", "--user"] if u else ["systemctl"]) + \
                ["list-units", "--type=service", "--all", "--no-pager", "--plain", "--no-legend"]
            out.append(run(cmd).stdout)
        return hash("".join(out))
    except Exception:
        return 0


def _watch_loop():
    last = {"ports": _fp_ports()}
    time.sleep(2)
    last["cron"] = _fp_cron()
    last["services"] = _fp_services()
    while True:
        try:
            cur = _fp_ports()
            if cur != last["ports"]:
                opened = sorted(p for p, _ in cur - last["ports"])
                closed = sorted(p for p, _ in last["ports"] - cur)
                bits = []
                if opened:
                    bits.append("opened " + ",".join(f":{p}" for p in opened))
                if closed:
                    bits.append("closed " + ",".join(f":{p}" for p in closed))
                last["ports"] = cur
                _note_change("ports", "; ".join(bits) or "ports changed")
            if int(time.time()) % 5 == 0:
                for kind, fn in (("cron", _fp_cron), ("services", _fp_services)):
                    c = fn()
                    if c != last[kind]:
                        last[kind] = c
                        _note_change(kind, f"{kind} changed")
        except Exception as e:
            try:
                with open(os.path.join(BASE, "server.log"), "a") as f:
                    f.write(f"watch error: {e}\n")
            except Exception:
                pass
        time.sleep(3)


@app.get("/api/versions")
def api_versions():
    with _ver_lock:
        return {"ok": True, "versions": dict(_versions), "changes": list(_changes)}


@app.get("/api/events")
def api_events():
    def gen():
        yield ": connected\n\n"
        last = None
        for _ in range(50):
            time.sleep(1)
            with _ver_lock:
                cur = dict(_versions)
            if cur != last:
                last = cur
                yield f"data: {json.dumps(cur)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------- db ---
def db():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS apps(
        id INTEGER PRIMARY KEY AUTOINCREMENT, port INTEGER,
        command TEXT, description TEXT, notes TEXT DEFAULT '',
        launch_cmd TEXT DEFAULT '', created INTEGER)""")
    return c


# ------------------------------------------------------- ai describe ---
# Rule-based describer (Spanish one-liners). If an LLM key exists, the
# frontend may call /api/describe which tries the LLM first, else falls back here.
PATTERNS = [
    (r"pi-web-server|pi-web-sessiond", "Servidor y daemon de PI WEB: la interfaz web de agentes que estás usando ahora."),
    (r"filex|serve_md", "FileX: servidor de archivos con render Markdown en el navegador."),
    (r"app\.py", "App Python (probable panel FastAPI/Flask): dashboard o herramienta local."),
    (r"uvicorn|gunicorn", "Servidor ASGI/WSGI: sirve una app web Python en producción local."),
    (r"http\.server|SimpleHTTPServer", "Servidor estático simple de Python: solo sirve archivos, sin lógica."),
    (r"node|bun|deno", "App JavaScript (Node/Bun): frontend SSR, API o herramienta de agentes."),
    (r"caddy", "Caddy: reverse-proxy HTTPS automático que enruta dominios a puertos internos."),
    (r"cloudflared", "Túnel Cloudflare: expone un puerto local a internet con URL pública."),
    (r"tailscaled|tailscale", "Tailscale: VPN mesh que da acceso privado a esta máquina."),
    (r"docker|containerd-shim", "Contenedor Docker en ejecución: app aislada con su propio filesystem."),
    (r"sshd|/sshd?:", "Servidor SSH: acceso remoto por terminal (puerto 22)."),
    (r"cups|ipp", "CUPS: servicio de impresión (IPP)."),
    (r"avahi", "Avahi mDNS: descubre impresoras y hosts .local en la LAN."),
    (r"NetworkManager|dnsmasq|systemd-resolve", "Red/DNS del sistema: resuelve nombres y gestiona conexiones."),
    (r"postgres|mysqld?|redis-server|mongo", "Base de datos local: guarda datos de alguna app."),
    (r"sddm|gdm|Xorg|wayland|gnome|kde|mutter|kwin", "Sesión gráfica del escritorio: dibuja tu pantalla."),
    (r"pipewire|pulseaudio|wireplumber", "Audio del sistema (PipeWire/PulseAudio)."),
    (r"bluetooth|ModemManager", "Hardware: bluetooth o módem gestionado por el sistema."),
    (r"snapd|fwupd|packagekit|apt", "Gestión de paquetes/firmware del sistema."),
    (r"transcribe_server|model_worker|nemo|parakeet", "Transcripción de voz Parakeet: convierte audio en subtítulos."),
    (r"chrome|chromium|firefox|brave", "Navegador abierto con depuración remota o automatización."),
    (r"ollama|llama|vllm|text-generation", "Servidor de LLM local: responde prompts por API."),
    (r"jupyter|ipython|notebook", "Jupyter: notebooks interactivos de Python."),
    (r"code-server|opencode|vscode", "IDE o agente de código servido en el navegador."),
    (r"socat|nginx|apache|traefik|haproxy", "Proxy/redirección de puertos hacia otro servicio."),
    (r"cron", "Planificador cron: ejecuta tareas programadas."),
    (r"netdata", "Netdata: monitor de CPU/RAM/disco en tiempo real."),
]


def ai_describe(command: str) -> str:
    cmd = (command or "").strip()
    if not cmd:
        return "Proceso sin línea de comando visible (quizá kernel o zombie)."
    low = cmd.lower()
    for pat, desc in PATTERNS:
        if re.search(pat, low):
            return desc
    # generic fallback: name the binary + args hint
    binary = cmd.split()[0].split("/")[-1]
    m = re.search(r"--port[ =](\d+)|:(\d{4,5})|port[ =](\d+)", low)
    hint = f" (usa el puerto {m.group(1) or m.group(2) or m.group(3)})" if m else ""
    return f"Programa `{binary}` corriendo con argumentos propios{hint}: revisa Inspeccionar para ver qué hace."


def llm_describe(command: str) -> str | None:
    """Try opencode-go / OpenAI-compatible LLM if a key exists, else None."""
    key = os.environ.get("OPENCODE_GO_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    base = os.environ.get("OPENCODE_GO_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENCODE_GO_MODEL", "gpt-4o-mini")
    try:
        req = urllib.request.Request(
            f"{base}/chat/completions",
            data=json.dumps({"model": model, "max_tokens": 80, "messages": [
                {"role": "user", "content": f"En una frase breve en español, ¿qué hace este programa corriendo en Linux? Comando: {command[:400]}"}]}).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


# ------------------------------------------------------------- ports ---
def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=kw.get("timeout", 15))


def proc_info(pid: int) -> dict:
    out = {"pid": pid, "user": "?", "cmdline": "", "cwd": "", "started": "", "mem_mb": 0}
    try:
        out["user"] = pwd.getpwuid(os.stat(f"/proc/{pid}").st_uid).pw_name
    except Exception:
        pass
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            out["cmdline"] = f.read().replace(b"\0", b" ").decode(errors="replace").strip()
    except Exception:
        pass
    try:
        out["cwd"] = os.readlink(f"/proc/{pid}/cwd")
    except Exception:
        pass
    try:
        p = run(["ps", "-o", "lstart=,rss=", "-p", str(pid)])
        parts = p.stdout.strip().rsplit(None, 1)
        if parts:
            out["started"] = parts[0].strip() if len(parts) == 2 else parts[0].strip()
            try:
                out["mem_mb"] = round(int(parts[-1]) / 1024, 1)
            except Exception:
                pass
    except Exception:
        pass
    return out


def probe_http(port: int) -> dict:
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/", method="HEAD")
        with urllib.request.urlopen(req, timeout=1.2) as r:
            return {"http": True, "status": r.status}
    except Exception as e:
        code = getattr(e, "code", None)
        return {"http": code is not None, "status": code or 0}


def scan_ports() -> list:
    p = run(["ss", "-tlnp"])
    found = {}  # port -> pid
    for line in p.stdout.splitlines():
        m = re.search(r"(?:^|\s)(?:\d+\.\d+\.\d+\.\d+|\[::\]|\*):(\d+)\s", line)
        if not m:
            continue
        port = int(m.group(1))
        pm = re.search(r'pid=(\d+)', line)
        pid = int(pm.group(1)) if pm else 0
        # keep first pid seen per port (ss may list several processes)
        if port not in found:
            found[port] = pid
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        jobs = {port: (ex.submit(proc_info, pid) if pid else None,
                       ex.submit(probe_http, port))
                for port, pid in found.items()}
        for port, (fi, fh) in jobs.items():
            info = fi.result() if fi else {"pid": 0, "user": "?", "cmdline": "", "cwd": "", "started": "", "mem_mb": 0}
            probe = fh.result()
            rows.append({"port": port, **info, **probe})
    rows.sort(key=lambda r: r["port"])
    return rows


@app.get("/api/ports")
def api_ports():
    hit = cache_get(("ports",))
    if hit is not None:
        d = dict(hit)
        d["cached"] = True
        return d
    rows = scan_ports()
    c = db()
    reg = {r[0]: {"id": r[0], "port": r[1], "command": r[2], "description": r[3],
                  "notes": r[4], "launch_cmd": r[5]}
           for r in c.execute("SELECT id, port, command, description, notes, launch_cmd FROM apps").fetchall()}
    c.close()
    by_port = {}
    for v in reg.values():
        by_port.setdefault(v["port"], v)
    for r in rows:
        rp = by_port.get(r["port"])
        r["registry"] = rp
        r["description"] = (rp["description"] if rp and rp["description"]
                            else ai_describe(r["cmdline"]))
    resp = {"ok": True, "rows": rows,
            "manual": [v for v in reg.values() if v["port"] not in {r["port"] for r in rows}]}
    cache_set(("ports",), resp, 4)
    return resp


@app.get("/api/describe")
def api_describe(command: str = ""):
    d = llm_describe(command) or ai_describe(command)
    return {"ok": True, "description": d, "llm": bool(llm_describe and d and os.environ.get("OPENCODE_GO_API_KEY"))}


@app.post("/api/kill")
async def api_kill(req: Request):
    b = await req.json()
    pid = int(b.get("pid", 0))
    sig = signal.SIGKILL if b.get("force") else signal.SIGTERM
    if pid <= 1:
        return {"ok": False, "error": "refusing to kill pid <= 1"}
    try:
        os.kill(pid, sig)
        cache_invalidate("ports", "inspect")
        return {"ok": True, "pid": pid, "signal": "KILL" if b.get("force") else "TERM"}
    except ProcessLookupError:
        return {"ok": False, "error": "process already gone"}
    except PermissionError:
        return {"ok": False, "error": "permission denied — process belongs to another user (try sudo in a terminal)"}


@app.get("/api/inspect")
def api_inspect(pid: int = 0):
    if pid <= 0:
        return {"ok": False, "error": "bad pid"}
    hit = cache_get(("inspect", pid))
    if hit is not None:
        d = dict(hit)
        d["cached"] = True
        return d
    info = proc_info(pid)
    try:
        info["fds"] = str(len(os.listdir(f"/proc/{pid}/fd")))
    except Exception:
        info["fds"] = "?"
    try:
        with open(f"/proc/{pid}/environ", "rb") as f:
            env = f.read().replace(b"\0", b"\n").decode(errors="replace")
        info["env"] = "\n".join(l for l in env.splitlines()
                                if not re.search(r"KEY|TOKEN|SECRET|PASS", l, re.I))[:2000]
    except Exception:
        info["env"] = ""
    p = run(["ss", "-tnp"])
    info["conns"] = "\n".join(l.strip() for l in p.stdout.splitlines()
                              if f"pid={pid}" in l)[:1500]
    resp = {"ok": True, **info}
    cache_set(("inspect", pid), resp, 2)
    return resp


@app.post("/api/launch")
async def api_launch(req: Request):
    b = await req.json()
    cmd = (b.get("cmd") or "").strip()
    if not cmd:
        return {"ok": False, "error": "empty command"}
    log = os.path.join(BASE, "launch.log")
    with open(log, "a") as f:
        f.write(f"\n$ {cmd}\n")
        subprocess.Popen(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True,
                         cwd=b.get("cwd") or BASE)
    cache_invalidate("ports")
    return {"ok": True, "log": "launch.log"}


# -------------------------------------------------------- apps (crud) ---
@app.get("/api/apps")
def api_apps():
    c = db()
    rows = [{"id": r[0], "port": r[1], "command": r[2], "description": r[3],
             "notes": r[4], "launch_cmd": r[5], "created": r[6]}
            for r in c.execute("SELECT * FROM apps ORDER BY port").fetchall()]
    c.close()
    return {"ok": True, "rows": rows}


@app.post("/api/apps")
async def api_apps_add(req: Request):
    b = await req.json()
    try:
        port = int(b.get("port", 0))
    except Exception:
        return {"ok": False, "error": "port must be a number"}
    if not (1 <= port <= 65535):
        return {"ok": False, "error": "port out of range"}
    desc = b.get("description") or ai_describe(b.get("command", ""))
    c = db()
    cur = c.execute("INSERT INTO apps(port, command, description, notes, launch_cmd, created)"
                    " VALUES (?,?,?,?,?,?)", (port, b.get("command", ""), desc,
                                              b.get("notes", ""), b.get("launch_cmd", ""),
                                              int(time.time())))
    c.commit()
    rid = cur.lastrowid
    c.close()
    cache_invalidate("ports")
    return {"ok": True, "id": rid, "description": desc}


@app.put("/api/apps/{rid}")
async def api_apps_edit(rid: int, req: Request):
    b = await req.json()
    c = db()
    c.execute("UPDATE apps SET port=?, command=?, description=?, notes=?, launch_cmd=? WHERE id=?",
              (int(b.get("port", 0)), b.get("command", ""), b.get("description", ""),
               b.get("notes", ""), b.get("launch_cmd", ""), rid))
    c.commit()
    c.close()
    cache_invalidate("ports")
    return {"ok": True, "id": rid}


@app.delete("/api/apps/{rid}")
def api_apps_del(rid: int):
    c = db()
    c.execute("DELETE FROM apps WHERE id=?", (rid,))
    c.commit()
    c.close()
    cache_invalidate("ports")
    return {"ok": True, "id": rid}


# ------------------------------------------------------------- cron ---
CRON_RE = re.compile(r"^(@\S+|(?:[\d\*,/\-]+\s+){5})(.*)$")


def parse_crontab(text: str) -> list:
    rows = []
    for i, line in enumerate(text.splitlines()):
        raw = line
        s = line.strip()
        if not s:
            rows.append({"i": i, "type": "blank", "raw": raw})
        elif s.startswith("#"):
            rows.append({"i": i, "type": "comment", "raw": raw})
        else:
            m = CRON_RE.match(s)
            if m:
                rows.append({"i": i, "type": "job", "schedule": m.group(1).strip(),
                             "command": m.group(2).strip(), "raw": raw})
            else:
                rows.append({"i": i, "type": "env", "raw": raw})
    return rows


def user_crontab() -> str:
    p = run(["crontab", "-l"])
    return p.stdout if p.returncode == 0 else ""


def write_crontab(text: str):
    bak = os.path.join(BASE, "crontab.bak")
    cur = user_crontab()
    with open(bak, "w") as f:
        f.write(cur)
    p = subprocess.run(["crontab", "-"], input=text, capture_output=True, text=True, timeout=15)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "crontab rejected the file")
    cache_invalidate("cron")
    return bak


@app.get("/api/cron")
def api_cron():
    hit = cache_get(("cron",))
    if hit is not None:
        d = dict(hit)
        d["cached"] = True
        return d
    user = user_crontab()
    data = {"ok": True, "user_jobs": parse_crontab(user), "system": {}}
    p = run(["cat", "/etc/crontab"])
    data["system"]["crontab"] = p.stdout if p.returncode == 0 else "(unreadable)"
    d = run(["sh", "-c", "for f in /etc/cron.d/*; do echo '### '\"$f\"; cat \"$f\" 2>/dev/null; echo; done"])
    data["system"]["cron_d"] = d.stdout[:6000]
    for per in ("hourly", "daily", "weekly", "monthly"):
        try:
            data["system"][per] = sorted(os.listdir(f"/etc/cron.{per}"))
        except Exception:
            data["system"][per] = []
    t = run(["systemctl", "list-timers", "--no-pager", "--plain"])
    data["system"]["timers"] = t.stdout[:4000] if t.returncode == 0 else "(unavailable)"
    cache_set(("cron",), data, 5)
    return data


def cron_lines():
    return user_crontab().splitlines()


@app.post("/api/cron")
async def api_cron_add(req: Request):
    b = await req.json()
    sched, cmd = (b.get("schedule") or "").strip(), (b.get("command") or "").strip()
    if not sched or not cmd or not CRON_RE.match(f"{sched} {cmd}"):
        return {"ok": False, "error": "bad schedule or empty command (e.g. '*/15 * * * *')"}
    tag = (b.get("tag") or "").strip()
    line = f"{sched} {cmd}" + (f" # {tag}" if tag else "")
    lines = cron_lines()
    text = "\n".join(lines + [line]).strip() + "\n"
    try:
        write_crontab(text)
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True}


@app.put("/api/cron/{idx}")
async def api_cron_edit(idx: int, req: Request):
    b = await req.json()
    lines = cron_lines()
    if not (0 <= idx < len(lines)):
        return {"ok": False, "error": "bad index"}
    sched, cmd = (b.get("schedule") or "").strip(), (b.get("command") or "").strip()
    if not sched or not cmd or not CRON_RE.match(f"{sched} {cmd}"):
        return {"ok": False, "error": "bad schedule or empty command"}
    lines[idx] = f"{sched} {cmd}"
    try:
        write_crontab("\n".join(lines).strip() + "\n")
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True}


@app.delete("/api/cron/{idx}")
def api_cron_del(idx: int):
    lines = cron_lines()
    if not (0 <= idx < len(lines)):
        return {"ok": False, "error": "bad index"}
    lines.pop(idx)
    try:
        write_crontab("\n".join(lines).strip() + "\n" if lines else "")
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True}


@app.post("/api/cron/toggle/{idx}")
def api_cron_toggle(idx: int):
    lines = cron_lines()
    if not (0 <= idx < len(lines)):
        return {"ok": False, "error": "bad index"}
    s = lines[idx].strip()
    if s.startswith("#"):
        body = s.lstrip("# ").rstrip()
        lines[idx] = body if CRON_RE.match(body) else lines[idx]
    elif s and not s.startswith("#"):
        lines[idx] = "# " + lines[idx]
    try:
        write_crontab("\n".join(lines).strip() + "\n")
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True}


@app.post("/api/cron/run")
async def api_cron_run(req: Request):
    b = await req.json()
    cmd = (b.get("command") or "").strip()
    if not cmd:
        return {"ok": False, "error": "empty command"}
    log = os.path.join(BASE, "cron_run.log")
    with open(log, "a") as f:
        f.write(f"\n$ {cmd}\n")
        subprocess.Popen(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    return {"ok": True, "log": "cron_run.log"}


# ---------------------------------------------------------- services ---
def list_services(user: bool) -> list:
    cmd = (["systemctl", "--user"] if user else ["systemctl"]) + \
        ["list-units", "--type=service", "--all", "--no-pager", "--plain", "--no-legend"]
    p = run(cmd)
    rows = []
    for line in p.stdout.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 4:
            continue
        rows.append({"unit": parts[0], "load": parts[1], "active": parts[2],
                     "sub": parts[3], "description": parts[4] if len(parts) > 4 else "",
                     "scope": "user" if user else "system"})
    return rows


@app.get("/api/services")
def api_services():
    hit = cache_get(("services",))
    if hit is not None:
        d = dict(hit)
        d["cached"] = True
        return d
    resp = {"ok": True, "system": list_services(False), "user": list_services(True)}
    cache_set(("services",), resp, 5)
    return resp


@app.post("/api/services/action")
async def api_svc_action(req: Request):
    b = await req.json()
    unit = (b.get("unit") or "").strip()
    act = (b.get("action") or "").strip()
    scope = (b.get("scope") or "system").strip()
    if not re.fullmatch(r"[\w@\-.:]+\.service", unit):
        return {"ok": False, "error": "bad unit name"}
    if act not in ("start", "stop", "restart", "enable", "disable"):
        return {"ok": False, "error": "bad action"}
    cmd = (["systemctl", "--user"] if scope == "user" else ["systemctl"]) + [act, unit]
    # enable/disable on system scope need root; run via sudo -n (fails cleanly if no rights)
    p = run(cmd, timeout=30)
    if p.returncode != 0:
        err = (p.stderr or p.stdout).strip()[:300] or "failed"
        hint = " — needs root; run it in a terminal with sudo" if scope == "system" else ""
        return {"ok": False, "error": err + hint}
    cache_invalidate("services")
    return {"ok": True}


@app.get("/api/services/logs")
def api_svc_logs(unit: str = "", scope: str = "system", n: int = 120):
    if not re.fullmatch(r"[\w@\-.:]+\.service", unit or ""):
        return {"ok": False, "error": "bad unit name"}
    cmd = (["journalctl", "--user"] if scope == "user" else ["journalctl"]) + \
        ["-u", unit, "-n", str(min(max(n, 20), 500)), "--no-pager"]
    hit = cache_get(("logs", unit, scope))
    if hit is not None:
        d = dict(hit)
        d["cached"] = True
        return d
    p = run(cmd, timeout=20)
    resp = {"ok": True, "logs": (p.stdout or p.stderr)[-8000:]}
    cache_set(("logs", unit, scope), resp, 10)
    return resp


@app.get("/api/services/file")
def api_svc_file(unit: str = "", scope: str = "system"):
    if not re.fullmatch(r"[\w@\-.:]+\.service", unit or ""):
        return {"ok": False, "error": "bad unit name"}
    cmd = (["systemctl", "--user"] if scope == "user" else ["systemctl"]) + ["cat", unit]
    p = run(cmd, timeout=15)
    return {"ok": True, "file": (p.stdout or p.stderr)[:6000]}


USER_DIR = os.path.expanduser("~/.config/systemd/user")


@app.get("/api/services/custom")
def api_svc_custom():
    try:
        files = sorted(f for f in os.listdir(USER_DIR) if f.endswith(".service"))
    except Exception:
        files = []
    out = []
    for f in files:
        try:
            with open(os.path.join(USER_DIR, f)) as fh:
                out.append({"unit": f, "content": fh.read()})
        except Exception:
            pass
    return {"ok": True, "rows": out}


@app.post("/api/services/custom")
async def api_svc_custom_add(req: Request):
    b = await req.json()
    name = (b.get("unit") or "").strip()
    if not re.fullmatch(r"[\w\-.]+\.service", name):
        return {"ok": False, "error": "name must be like my-app.service"}
    desc = b.get("description", "custom service") or "custom service"
    exec_start = (b.get("exec") or "").strip()
    if not exec_start:
        return {"ok": False, "error": "ExecStart is required"}
    content = (f"[Unit]\nDescription={desc}\nAfter=network.target\n\n"
               f"[Service]\nExecStart={exec_start}\nRestart=on-failure\n\n"
               f"[Install]\nWantedBy=default.target\n")
    os.makedirs(USER_DIR, exist_ok=True)
    with open(os.path.join(USER_DIR, name), "w") as f:
        f.write(content if b.get("raw") is None else b.get("raw"))
    run(["systemctl", "--user", "daemon-reload"])
    cache_invalidate("services")
    return {"ok": True, "unit": name}


@app.put("/api/services/custom/{unit}")
async def api_svc_custom_edit(unit: str, req: Request):
    if not re.fullmatch(r"[\w\-.]+\.service", unit):
        return {"ok": False, "error": "bad unit name"}
    b = await req.json()
    path = os.path.join(USER_DIR, unit)
    if not os.path.exists(path):
        return {"ok": False, "error": "not a custom user unit"}
    with open(path, "w") as f:
        f.write(b.get("content", ""))
    run(["systemctl", "--user", "daemon-reload"])
    cache_invalidate("services")
    return {"ok": True, "unit": unit}


@app.delete("/api/services/custom/{unit}")
def api_svc_custom_del(unit: str):
    if not re.fullmatch(r"[\w\-.]+\.service", unit):
        return {"ok": False, "error": "bad unit name"}
    path = os.path.join(USER_DIR, unit)
    if not os.path.exists(path):
        return {"ok": False, "error": "not a custom user unit"}
    run(["systemctl", "--user", "disable", unit])
    os.remove(path)
    run(["systemctl", "--user", "daemon-reload"])
    cache_invalidate("services")
    return {"ok": True, "unit": unit}


# -------------------------------------------------------------- stats ---
# 1s sampler -> per-timeframe OHLC candles, persisted in sqlite.
STATS_TFS = [("1s", 1), ("30s", 30), ("5m", 300), ("1h", 3600), ("8h", 28800), ("1d", 86400)]
STATS_DEFAULT_N = {"1s": 60, "30s": 10, "5m": 10, "1h": 10, "8h": 10, "1d": 10}
STATS_MAX = 500  # max candles kept per timeframe; ?n= clamps to this

_stats_lock = threading.Lock()
_stats_data = {tf: {"period": p, "win": None,
                     "candles": collections.deque(maxlen=STATS_MAX)}
                for tf, p in STATS_TFS}
_stats_latest = {}
_prev_cpu = None
_prev_net = None


def stats_tables(c):
    c.execute("CREATE TABLE IF NOT EXISTS stat_candles(tf TEXT, t0 INTEGER, metrics TEXT, PRIMARY KEY (tf, t0))")


def sample_system() -> dict:
    global _prev_cpu, _prev_net
    out = {}
    try:
        with open("/proc/stat") as f:
            vals = list(map(int, f.readline().split()[1:]))
        idle, total = vals[3] + vals[4], sum(vals)
        if _prev_cpu and total > _prev_cpu[1]:
            out["cpu"] = round(100 * (1 - (idle - _prev_cpu[0]) / (total - _prev_cpu[1])), 1)
        else:
            out["cpu"] = 0.0
        _prev_cpu = (idle, total)
    except Exception:
        out["cpu"] = 0.0
    try:
        mi = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":")
                mi[k] = int(v.split()[0])
        out["mem"] = round(100 * (1 - mi["MemAvailable"] / mi["MemTotal"]), 1)
    except Exception:
        out["mem"] = 0.0
    try:
        rx = tx = 0
        with open("/proc/net/dev") as f:
            for line in f:
                if ":" not in line:
                    continue
                iface, rest = line.split(":")
                if iface.strip() == "lo":
                    continue
                flds = rest.split()
                rx += int(flds[0])
                tx += int(flds[8])
        now = time.time()
        if _prev_net:
            dt = max(now - _prev_net[0], 0.2)
            out["net_rx"] = round(max(rx - _prev_net[1], 0) / dt / 1024, 1)
            out["net_tx"] = round(max(tx - _prev_net[2], 0) / dt / 1024, 1)
        else:
            out["net_rx"] = out["net_tx"] = 0.0
        _prev_net = (now, rx, tx)
    except Exception:
        out.setdefault("net_rx", 0.0)
        out.setdefault("net_tx", 0.0)
    try:
        st = os.statvfs("/")
        out["disk_root"] = round(100 * (1 - st.f_bavail / st.f_blocks), 1)
        if os.path.ismount("/home"):
            sth = os.statvfs("/home")
            out["disk_home"] = round(100 * (1 - sth.f_bavail / sth.f_blocks), 1)
    except Exception:
        out.setdefault("disk_root", 0.0)
    try:
        out["load1"] = round(os.getloadavg()[0], 2)
    except Exception:
        out["load1"] = 0.0
    return out


def stats_tick():
    ts = int(time.time())
    s = sample_system()
    with _stats_lock:
        _stats_latest.clear()
        _stats_latest.update({"t": ts, **s})
        for tf, period in STATS_TFS:
            st = _stats_data[tf]
            t0 = ts - (ts % period)
            w = st["win"]
            if w is None or w["t"] != t0:
                if w is not None:
                    st["candles"].append(w)
                st["win"] = {"t": t0, "m": {k: [v, v, v, v] for k, v in s.items()}}
            else:
                for k, v in s.items():
                    c = w["m"].get(k)
                    w["m"][k] = [c[0], max(c[1], v), min(c[2], v), v] if c else [v, v, v, v]


def stats_save():
    try:
        with _stats_lock:
            snap = {tf: list(st["candles"])[-STATS_MAX:] for tf, st in _stats_data.items()}
        c = sqlite3.connect(DB)
        stats_tables(c)
        for tf, rows in snap.items():
            c.execute("DELETE FROM stat_candles WHERE tf=?", (tf,))
            c.executemany("INSERT OR REPLACE INTO stat_candles VALUES (?,?,?)",
                          [(tf, r["t"], json.dumps(r["m"])) for r in rows])
        c.commit()
        c.close()
    except Exception as e:
        try:
            with open(os.path.join(BASE, "server.log"), "a") as f:
                f.write(f"stats_save error: {e}\n")
        except Exception:
            pass


def stats_load():
    try:
        c = sqlite3.connect(DB)
        stats_tables(c)
        for tf, _ in STATS_TFS:
            rows = c.execute("SELECT t0, metrics FROM stat_candles WHERE tf=? ORDER BY t0", (tf,)).fetchall()
            with _stats_lock:
                dq = _stats_data[tf]["candles"]
                dq.clear()
                for t0, m in rows[-STATS_MAX:]:
                    dq.append({"t": t0, "m": json.loads(m)})
        c.close()
    except Exception:
        pass


def _stats_loop():
    tick = 0
    while True:
        try:
            stats_tick()
            tick += 1
            if tick % 60 == 0:
                stats_save()
        except Exception as e:
            try:
                with open(os.path.join(BASE, "server.log"), "a") as f:
                    f.write(f"stats error: {e}\n")
            except Exception:
                pass
        time.sleep(1)


@app.get("/api/stats/meta")
def api_stats_meta():
    with _stats_lock:
        latest = dict(_stats_latest)
    metrics = sorted(k for k in latest if k != "t")
    return {"ok": True, "tfs": [tf for tf, _ in STATS_TFS], "defaults": STATS_DEFAULT_N,
            "max": STATS_MAX, "metrics": metrics, "latest": latest}


@app.get("/api/stats")
def api_stats(tf: str = "1s", n: int = 0):
    periods = dict(STATS_TFS)
    if tf not in periods:
        tf = "1s"
    if not n:
        n = STATS_DEFAULT_N[tf]
    n = max(2, min(int(n), STATS_MAX))
    with _stats_lock:
        st = _stats_data[tf]
        rows = list(st["candles"])[-n:]
        win = dict(st["win"]) if st["win"] else None
        latest = dict(_stats_latest)
    out = [{"t": r["t"], "m": r["m"]} for r in rows]
    if win:
        out = (out + [{"t": win["t"], "m": win["m"], "partial": True}])[-n:]
    return {"ok": True, "tf": tf, "period": periods[tf], "n": n,
            "candles": out, "latest": latest}


# --------------------------------------------------------------- web ---
@app.get("/health")
def health():
    return {"ok": True, "exp": "e067-sys-panel"}


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(BASE, "static", "index.html")) as f:
        return f.read()


app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")

stats_load()
if not os.environ.get("E067_NOSTATS"):
    threading.Thread(target=_stats_loop, daemon=True).start()
threading.Thread(target=_watch_loop, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
