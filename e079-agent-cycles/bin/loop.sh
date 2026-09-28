#!/bin/bash
# e079 forever leg (dumb, $0 cost): keep exactly one cycle moving.
# cron: */30 * * * * .../bin/loop.sh >> .../data/loop.log 2>&1
# Intelligent code-writing legs are agent sessions (or RUNNER_PROMPT.md
# via pi --print, which spends AI budget — OFF by default for margin).
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=$(python3 -c "import json;print(json.load(open('$DIR/needs.json'))['port'])")
STALE=$(python3 -c "import json;print(json.load(open('$DIR/needs.json')).get('loop_stale_minutes',120))")
LOG="$DIR/data/loop_log.jsonl"
NOW=$(date +%s)

leg() { echo "{\"ts\":$NOW,\"event\":\"$1\",\"detail\":\"$2\"}" >> "$LOG"; }

# kill switch — Admin toggle or `touch data/STOP`
[ -f "$DIR/data/STOP" ] && { leg "skipped" "STOP set"; exit 0; }

# self-heal: restart server if dark (kill by exact port pid, never pkill)
if ! curl -sf --max-time 5 127.0.0.1:$PORT/api/version >/dev/null 2>&1; then
  PID=$(ss -tlnp 2>/dev/null | grep ":$PORT " | grep -oP 'pid=\K[0-9]+' | head -n1)
  [ -n "$PID" ] && kill "$PID" 2>/dev/null
  nohup python3 "$DIR/server/app.py" > "$DIR/data/server.log" 2>&1 &
  sleep 2
  leg "healed" "server restarted"
fi

lane_state() {
  # free = lane open AND goals queued (worth another chained pass)
  python3 - "$DIR" "$PORT" <<'PY2'
import json, sys, urllib.request
DIR, PORT = sys.argv[1], sys.argv[2]
try:
    cyc = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/cycles", timeout=10))
    goals = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/goals", timeout=10))
    print("running" if any(isinstance(c, dict) and c.get("status") == "running" for c in cyc)
          else ("free" if any(g.get("status") == "queued" for g in goals) else "empty"))
except Exception:
    print("dark")
PY2
}

one_leg() {
python3 - "$DIR" "$PORT" "$STALE" "$NOW" <<'PY'
import json, sys, urllib.request
DIR, PORT, STALE, NOW = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])

def api(path, payload=None):
    url = f"http://127.0.0.1:{PORT}{path}"
    data = json.dumps(payload or {}).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=10))
    except Exception as e:
        return {"_err": str(e)}

def leg(event, detail=""):
    with open(f"{DIR}/data/loop_log.jsonl", "a") as f:
        f.write(json.dumps({"ts": NOW, "event": event, "detail": detail}) + "\n")

cycles = api("/api/cycles")
if isinstance(cycles, dict) and cycles.get("_err"):
    leg("blocked", "api dark: " + cycles["_err"]); sys.exit(0)

running = [c for c in cycles if isinstance(c, dict) and c.get("status") == "running"]
# reconcile goals: active goals whose cycle is done -> done
try:
    with open(f"{DIR}/data/goals.jsonl") as f: goals = [json.loads(l) for l in f if l.strip()]
except Exception: goals = []
done_ids = {c["id"] for c in cycles if c.get("status") == "done"}
changed = False
for g in goals:
    if g.get("status") == "active" and g.get("cycle") in done_ids:
        g["status"] = "done"; changed = True
if changed:
    with open(f"{DIR}/data/goals.jsonl", "w") as f:
        for g in goals: f.write(json.dumps(g) + "\n")

# self-unstick: silent legs void themselves. A leg whose stream status has not
# updated in 15+ min (and is older than 15 min) is wedged: TERM its exact worker
# (found by cycle id in cmdline, bracket trick so pgrep never matches itself),
# void the cycle (no version for no work), free the lane. No human unsticks.
import os as _os, subprocess as _sp
def _api_post(path, payload, token=""):
    url = f"http://127.0.0.1:{PORT}{path}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json",
                                                           "X-Admin-Token": token})
    try:
        return json.load(urllib.request.urlopen(req, timeout=10))
    except Exception as e:
        return {"_err": str(e)}
try:
    _tok = json.load(open(f"{DIR}/needs.json")).get("admin_token", "")
except Exception:
    _tok = ""
for _c in list(running):
    _cid = _c["id"]
    _age = NOW - int(_c.get("started_ts", NOW))
    if _age < 900: continue
    try:
        _st = json.load(open(f"{DIR}/public/legs/{_cid}.status.json"))
        _silent = NOW - int(_st.get("updated_ts", _st.get("started_ts", NOW)))
    except Exception:
        # No stream at all: judge by birth, not heartbeat. A leg that never
        # narrated in 15+ min is silent by definition (c010 class: wedged
        # before streaming). Skipping it here would block the lane forever.
        _silent = _age
    if _silent < 900: continue
    _pat = f"cycle {_cid[:-1]}[{_cid[-1]}]"
    try:
        _pids = _sp.run(["pgrep", "-f", _pat], capture_output=True, text=True, timeout=5).stdout.split()
    except Exception:
        _pids = []
    _killed = []
    for _p in _pids:
        try:
            _os.kill(int(_p), 15); _killed.append(_p)
        except Exception:
            pass
    _v = _api_post("/api/cycle/void", {"id": _cid, "reason": f"keeper: stream silent {_silent//60}min, worker TERMd {_killed}"}, _tok)
    if _v.get("status") == "void":
        leg("auto-void", f"{_cid} silent {_silent//60}min, TERM {_killed}, lane freed")
        running = [x for x in running if x["id"] != _cid]
    else:
        leg("blocked", f"void {_cid} failed: {_v.get('error', _v)}")
if running:
    r = running[0]
    age = NOW - int(r.get("started_ts", NOW))
    if age > STALE * 60:
        fin = api("/api/cycle/finish", {"id": r["id"], "notes": "loop: stale auto-finish, frees the lane"})
        leg("auto-finish", f'{r["id"]} age {age//60}min -> {fin.get("produced_version", "?")}')
    else:
        leg("heartbeat", f'{r["id"]} running {age//60}min, lane busy')
else:
    nxt = next((g for g in goals if g.get("status") == "queued"), None)
    import os as _os
    thinker = _os.path.exists(f"{DIR}/data/THINKER")
    if not nxt:
        leg("idle", "no queued goals, lane open")
    elif not thinker:
        nq = sum(1 for g in goals if g.get("status") == "queued")
        leg("ready", f"{nq} goal(s) wait for a thinker — lane left open, nothing auto-started")
    else:
        started = api("/api/cycle/start", {"goal": nxt["goal"]})
        if started.get("id"):
            for g in goals:
                if g is nxt: g["status"] = "active"; g["cycle"] = started["id"]
            with open(f"{DIR}/data/goals.jsonl", "w") as f:
                for g in goals: f.write(json.dumps(g) + "\n")
            leg("auto-start", f'{started["id"]}: {nxt["goal"][:80]}')
        else:
            leg("blocked", "start failed: " + str(started.get("error", "?")))
PY
}
# chain: TURBO mode runs legs back-to-back (no 30-min wait between cycles).
# Normal mode = exactly one pass per invocation.
CHAIN=1
[ -f "$DIR/data/TURBO" ] && CHAIN=10
for ((i = 1; i <= CHAIN; i++)); do
  one_leg
  [ "$i" -ge "$CHAIN" ] && break
  [ "$(lane_state)" = "free" ] || break
done
# workers census: keeper observes (server cannot see processes). Written every pass.
# Matching: cmdline must contain BOTH the pi binary and "cycle <id>".
# Probes never contain "bin/pi", so self-match is impossible by construction.
python3 - "$DIR" <<'PY2'
import json, os, sys, time
DIR = sys.argv[1]
now = int(time.time())
import urllib.request
try:
    port = json.load(open(f"{DIR}/needs.json"))["port"]
    cyc = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/cycles", timeout=10))
except Exception:
    cyc = []
me = os.getpid()
procs = []
for pid in os.listdir("/proc"):
    if not pid.isdigit() or int(pid) == me: continue
    try:
        cl = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode("utf8", "replace")
        parts = open(f"/proc/{pid}/stat").read().split()
        procs.append((pid, cl, int(parts[13]) + int(parts[14])))
    except Exception:
        pass
legs = {}
for c in cyc:
    if not isinstance(c, dict) or c.get("status") != "running": continue
    cid = c["id"]
    w = [p for p in procs if "bin/pi" in p[1] and f"cycle {cid}" in p[1]]
    try:
        st = json.load(open(f"{DIR}/public/legs/{cid}.status.json"))
        sa = now - int(st.get("updated_ts", st.get("started_ts", now)))
    except Exception:
        sa = None
    try:
        la = now - int(os.path.getmtime(f"{DIR}/public/legs/{cid}.log"))
    except Exception:
        la = None
    legs[cid] = {"alive": bool(w), "pid": w[0][0] if w else None,
                 "cpu_ticks": w[0][2] if w else 0,
                 "status_age_s": sa, "log_age_s": la}
json.dump({"ts": now, "legs": legs}, open(f"{DIR}/data/workers.json", "w"))
PY2
# trajectory watch: bark only when the alert state CHANGES (no spam)
python3 - "$DIR" "$PORT" <<'PY2'
import json, sys, urllib.request
DIR, PORT = sys.argv[1], sys.argv[2]
try:
    lp = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/loop", timeout=10))
    cur = lp.get("alert")
    prev = None
    try:
        rows = [json.loads(l) for l in open(f"{DIR}/data/loop_log.jsonl") if l.strip()]
        al = [r for r in rows if r.get("event") in ("alert", "alert-clear")]
        prev = al[-1].get("detail") if al else None
    except Exception:
        pass
    import time
    def _leg(e, d):
        open(f"{DIR}/data/loop_log.jsonl", "a").write(json.dumps({"ts": int(time.time()), "event": e, "detail": d}) + "\n")
    if cur and cur != prev:
        _leg("alert", cur)
    elif not cur and prev:
        _leg("alert-clear", "trajectory nominal")
except Exception as e:
    pass
PY2
# smoke: board still serves after whatever we did (inline curl — never call test/check.sh here, it calls us)
if curl -sf --max-time 5 127.0.0.1:$PORT/ >/dev/null 2>&1; then leg "check" "PASS"; else leg "check" "FAIL"; fi
