#!/usr/bin/env python3
"""
cadence-monitor.py — deterministic heartbeat + hygiene audit of the agent fleet.

Pure mechanical loop: every TICK (5s) it:
  A. PROGRESS  — checks each known agent whose next_check_at has arrived, computes
     a status (NOT_STARTED|WORKING|IDLE|STUCK|DONE) from heartbeats + deliverables,
     and logs to progress-monitor.log + anomalies.md.
  B. HYGIENE   — every AUDIT_SEC (30s) takes a system snapshot and classifies
     resource/hybrid risks into resource-audit.log where the Cadence mind reads them.

It OBEYS config.json (interval per agent = N; cap floor/ceiling = quiet window).
The thinking part lives in the Cadence LLM agent which tunes config.json and the
caps via set-caps.sh.

Evidence per agent (progress):
  - heartbeat: last epoch in progress/<agent>.jsonl            (what the agent says)
  - output dir mtime: newest file mtime inside the agent dir      (what it produced)
  - done.txt presence                                              (finished?)
Statuses: NOT_STARTED | WORKING | IDLE | STUCK | DONE
  - NOT_STARTED if no heartbeat AND no output files AND no done.txt
  - WORKING     if evidence younger than max(3*tick, 30s) OR heartbeat exists
  - IDLE        if evidence older than N*2 but heartbeat exists (agent alive, slow)
  - STUCK       if evidence older than N*4 with no evolution
  - DONE        if done.txt exists

Hygiene dimensions (resource-audit.log, one JSON object per audit):
  - quiet_hours  : whether now is inside the configured quiet window (config.time.quiet)
  - load         : 1/5/15 min load averages
  - mem          : used / total GiB
  - agent_cpu    : aggregate %CPU of processes in the agents cgroup (if readable)
  - cap          : configured cpu% / mem GiB
  - overshoot    : bool — agents exceeding the active cap
  - cpu_vs_gpu   : running encoders — is anything encoding video/audio on CPU?
  - chrome       : chrome processes running with --disable-gpu / swiftshader (CPU render instead of GPU)
  - idle_agents  : agents with status IDLE or STUCK in the last cycle
  Each line is classified level=info|warn|crit so the mind can filter cheaply.
"""

import json, os, time, datetime, subprocess, re, glob

PM_DIR = os.path.dirname(os.path.abspath(__file__))
PROG_DIR = os.path.join(PM_DIR, "progress")
STATE = os.path.join(PM_DIR, "monitor-state.json")
CONFIG = os.path.join(PM_DIR, "config.json")
LOGF = os.path.join(PM_DIR, "progress-monitor.log")
ANOM = os.path.join(PM_DIR, "anomalies.md")
RESLOG = os.path.join(PM_DIR, "resource-audit.log")
AGENTS_CG = "/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/agents-limited"

TICK = 5
AUDIT_SEC = 30
STUCK_REPEAT_SECS = 600

def now(): return int(time.time())
def ts(): return datetime.datetime.now().astimezone().isoformat(timespec="seconds")
def now_hm():
    d = datetime.datetime.now().astimezone()
    return d.hour * 60 + d.minute

OVERRIDE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quiet-override")

def quiet_override_state():
    """Returns 'off' if the user manually disabled quiet mode (persists until
    re-enabled), 'on' if manually forced on, else None (schedule applies)."""
    try:
        with open(OVERRIDE_FILE) as f:
            return f.read().strip().lower()
    except Exception:
        return None

def set_quiet_override(state):
    """state: 'off' | 'on' | None (remove override). Used by cadence or a human."""
    if state is None:
        try: os.remove(OVERRIDE_FILE)
        except FileNotFoundError: pass
    else:
        with open(OVERRIDE_FILE, "w") as f:
            f.write(state)
    return quiet_override_state()

def load(path, default):
    try:
        with open(path) as f: return json.load(f)
    except Exception:
        return default

def save(path, obj):
    with open(path, "w") as f: json.dump(obj, f, indent=2)

def default_agent_dir(agent):
    root = os.path.abspath(os.path.join(PM_DIR, "..", "..", ".."))
    for cand in (os.path.join(root, "e032-ai-skills-digest", agent),):
        if os.path.isdir(cand):
            return cand
    import glob
    matches = [p for p in glob.glob(os.path.join(root, "e*", agent)) if os.path.isdir(p)]
    return matches[0] if matches else os.path.join(root, agent)

def last_epoch(agent):
    p = os.path.join(PROG_DIR, agent + ".jsonl")
    try:
        with open(p) as f:
            last = None
            for line in f:
                line = line.strip()
                if line:
                    try: last = json.loads(line).get("epoch")
                    except Exception: pass
            return last
    except Exception:
        return None

def output_mtime(agent_dir):
    if not agent_dir or not os.path.isdir(agent_dir):
        return None
    newest = None
    for root, dirs, files in os.walk(agent_dir):
        if "output" in root:
            for f in files:
                if f.startswith("."): continue
                try:
                    m = os.path.getmtime(os.path.join(root, f))
                    if newest is None or m > newest: newest = m
                except Exception: pass
    return newest

def cgroup_read(path, default="n/a"):
    try:
        with open(path) as f: return f.read().strip()
    except Exception:
        return default

def sysrun(cmd, timeout=5):
    try:
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout
        return out
    except Exception:
        return ""

def live_board(config, state, now_t):
    """Write the ONE-PLACE live status board every tick:
    - <exp>/cadence/live.md  — human-readable markdown
    - <exp>/cadence/live.json — structured (served to the filex dashboard via SSE)
    Shows, per agent: window, alive?, CPU%, status, last step, evidence age.
    """
    # destination: <experiment>/cadence/live.{md,json} (derived from first agent dir)
    agent_cfgs = list(config.get("agents", {}).items())
    if not agent_cfgs:
        return
    first_dir = agent_cfgs[0][1].get("dir", "")
    exp_root = os.path.abspath(os.path.join(first_dir, "..", ".."))
    os.makedirs(os.path.join(exp_root, "cadence"), exist_ok=True)
    live_path = os.path.join(exp_root, "cadence", "live.md")
    live_json = os.path.join(exp_root, "cadence", "live.json")

    rows = []
    n_alive = n_work = n_done = n_bad = 0
    for agent, cfg in agent_cfgs:
        win = cfg.get("window", "?")
        pane_pid = sysrun(f"tmux display-message -t {win} -p '#{{pane_pid}}' 2>/dev/null").strip()
        cpu = ""
        alive = False
        if pane_pid:
            tree = sysrun(f"ps -o pid,pcpu,comm --ppid {pane_pid} 2>/dev/null; ps -p {pane_pid} -o pid,pcpu,comm --no-headers 2>/dev/null")
            if tree.strip():
                rows_l = [l.split() for l in tree.strip().splitlines() if l.strip()]
                if rows_l:
                    maxcpu = max((float(r[1]) for r in rows_l if len(r) >= 2 and _isnum(r[1])), default=0)
                    cpu = f"{maxcpu:.0f}"
                    alive = True
        st = state["agents"].get(agent, {})
        status = st.get("last_status", "?")
        cpu_f = float(cpu) if _isnum(cpu) else 0.0
        if status in ("NOT_STARTED", "IDLE") and cpu_f > 30:
            status = "BOOTING"
        age = st.get("last_age")
        hb = last_epoch(agent)
        hb_age = now_t - hb if hb else None
        step = _last_step(agent) or st.get("last_step", "") or ("no heartbeat yet — process consuming CPU" if cpu_f > 30 else "")

        if status == "DONE":
            n_done += 1
        elif status in ("STUCK", "NOT_STARTED"):
            n_bad += 1
        if status in ("WORKING", "BOOTING") and (cpu_f > 5 or (hb_age or 9999) < 120):
            n_work += 1
        if alive:
            n_alive += 1

        # URL of the agent's own folder (parent of the output/ dir that the
        # config `dir` points at). One line, no heuristics.
        agent_dir = cfg.get("dir", "")
        url = ""
        home = os.path.expanduser("~")
        if agent_dir.startswith(home):
            url = "/files/" + os.path.dirname(agent_dir)[len(home):].strip("/")

        rows.append({
            "agent": agent, "window": win, "alive": alive,
            "cpu": cpu or "—", "status": status,
            "step": step.replace("|", "/")[:80],
            "age_s": _humans(age) if age is not None else "—",
            "age_secs": int(age) if age is not None else None,
            "hb_age_secs": hb_age,
            "url": url,
        })

    n_busy = n_work + n_bad
    if n_busy > 0:
        engine = {"level": "producing", "text": f"🔥 {n_work} working · {n_done} done · {n_bad} stuck — the loop is producing."}
    elif n_done == len(agent_cfgs) and n_done > 0:
        engine = {"level": "stalled", "text": f"⛔ ALL {n_done} agents DONE and nothing queued — the loop is STALLED. A successor must be launched."}
    else:
        engine = {"level": "waiting", "text": f"{n_work} working · {n_done} done · {n_bad} stuck — waiting for work."}

    data = {
        "ts": ts(), "ts_epoch": now_t,
        "summary": {"alive": n_alive, "working": n_work, "done": n_done, "stuck": n_bad},
        "engine": engine,
        "agents": rows,
    }

    # markdown (human)
    lines = []
    lines.append(f"# LIVE — agent status · {data['ts']}")
    lines.append("_(updated every ~5s by the cadence clock)_")
    lines.append("")
    lines.append("| agent | win | alive | cpu% | status | last step | ev.age |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(f"| {r['agent']} | {r['window']} | {'yes' if r['alive'] else 'no'} | {r['cpu']} | {r['status']} | {r['step']} | {r['age_s']} |")
    lines.append("")
    lines.append(f"**engine:** {engine['text']}")
    lines.append("")
    lines.append("_legend: WORKING/BOOTING + cpu>5% or fresh evidence = working. DONE agents drawing their idle screen do NOT count._")
    try:
        with open(live_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        with open(live_json, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except Exception:
        pass

def _isnum(x):
    try:
        float(x); return True
    except Exception:
        return False

def _humans(secs):
    """Humanize seconds: 45s, 3m, 1.2h, 7.2h."""
    try:
        secs = float(secs)
    except Exception:
        return "—"
    if secs < 60:
        return f"{int(secs)}s"
    if secs < 3600:
        return f"{secs/60:.0f}m"
    return f"{secs/3600:.1f}h"

def _last_step(agent):
    p = os.path.join(PROG_DIR, agent + ".jsonl")
    try:
        with open(p) as f:
            last = None
            for line in f:
                if line.strip():
                    try: last = json.loads(line).get("step")
                    except Exception: pass
            return last
    except Exception:
        return None

def audit(config):
    entry = {"ts": ts(), "level": "info", "dimensions": {}}
    dims = entry["dimensions"]

    # quiet window model from config (user override wins: manual 'off' = never
    # quiet, manual 'on' = always quiet)
    qt = config.get("time", {})
    quiet = qt.get("quiet", {})
    quiet_start = quiet.get("start_hour_min", 22*60)   # default 22:00
    quiet_end   = quiet.get("end_hour_min", 7*60)      # default 07:00
    ov = quiet_override_state()
    if ov == "off":
        in_quiet = False
    elif ov == "on":
        in_quiet = True
    else:
        hm = now_hm()
        if quiet_start <= quiet_end:
            in_quiet = quiet_start <= hm < quiet_end
        else:  # wraps midnight
            in_quiet = hm >= quiet_start or hm < quiet_end
    dims["quiet_hours"] = in_quiet
    dims["quiet_override"] = ov  # 'off'/'on'/null so the mind knows why

    # load average
    try:
        la = [float(x) for x in os.getloadavg()]
        dims["load"] = [round(x,2) for x in la]
    except Exception:
        dims["load"] = None

    # memory
    try:
        with open("/proc/meminfo") as f:
            kv = {}
            for line in f:
                k, v = line.split(":"); kv[k.strip()] = int(v.split()[0])
        used_gb = (kv["MemTotal"] - kv["MemAvailable"]) / 1048576
        total_gb = kv["MemTotal"] / 1048576
        dims["mem"] = {"used_gb": round(used_gb,1), "total_gb": round(total_gb,1)}
    except Exception:
        dims["mem"] = None

    # agents cgroup: aggregate usage.
    # cpu.stat usage/100000 = core-seconds used; compare to quota.
    cpu_stat = cgroup_read(os.path.join(AGENTS_CG, "cpu.stat"))
    usage_cores = total_core_ms = None
    try:
        u = int(re.search(r"usage_usec (\d+)", cpu_stat).group(1))
        usage_cores = u / 1_000_000
    except Exception:
        pass
    cap_cpu = cgroup_read(os.path.join(AGENTS_CG, "cpu.max"), "max 100000")
    try:
        q, p = cap_cpu.split()
        cap_cores = None if q.lower() == "max" else int(q)/100000
    except Exception:
        cap_cores = None
    mem_max = cgroup_read(os.path.join(AGENTS_CG, "memory.max"))
    try:
        cap_mem_gb = int(mem_max) / 1073741824
    except Exception:
        cap_mem_gb = None
    dims["agent_usage_cores_total_sec"] = round(usage_cores,1) if usage_cores is not None else None
    dims["agent_cap_cores"] = cap_cores
    dims["agent_cap_mem_gb"] = cap_mem_gb
    dims["overshoot_cap"] = None  # microbursts irrelevant; mind uses period-average

    # unsubmitted-Enter detection: a message typed at an agent's prompt that was
    # never submitted (the classic "sent instruction without Enter" failure).
    # Heuristic: capture ALL windows, sleep once, capture again; any window whose
    # pane is IDENTICAL both times AND has a substantive "❯"-message line is
    # flagged. Also flag DEAD_WINDOW when the pane's owning process is just a
    # shell (the agent binary exited, input stranded).
    unsub, dead = [], []
    wins = [(agent, cfg.get("window")) for agent, cfg in config.get("agents", {}).items() if cfg.get("window")]
    if wins:
        p1_all = {w: sysrun(f"tmux capture-pane -t {w} -p 2>/dev/null") for _, w in wins}
        time.sleep(2.5)
        p2_all = {w: sysrun(f"tmux capture-pane -t {w} -p 2>/dev/null") for _, w in wins}
        for agent, win in wins:
            p1, p2 = p1_all.get(win), p2_all.get(win)
            if not p1 or not p2:
                continue
            lines1 = [l.rstrip() for l in p1.splitlines() if l.strip()]
            lines2 = [l.rstrip() for l in p2.splitlines() if l.strip()]
            if lines1 != lines2:
                continue  # pane is moving = agent alive and working
            # a stranded input line: the ❯ prompt carrying a LONG message.
            # Filter out idle-placeholder prompts (cmd's "Ask your question...",
            # opencode's empty prompt) — a real stranded instruction is substantive.
            idle_placeholders = ("ask your question", "type your message", "type a message", "say something")
            dangling = None
            for l in lines1:
                mm = re.search(r"^❯\s+(.{15,})", l)
                if not mm:
                    continue
                text = mm.group(1).strip().lower()
                if any(p in text for p in idle_placeholders):
                    continue
                if len(mm.group(1).strip()) < 30:
                    continue  # too short to be a stranded instruction
                dangling = l[:90]
                break
            if dangling and "esc interrupt" not in p2:
                # owning process: is the agent binary still there, or just a shell?
                ppid = sysrun(f"tmux display-message -t {win} -p '#{{pane_pid}}' 2>/dev/null").strip()
                proc = sysrun(f"ps -p {ppid} -o comm= 2>/dev/null").strip() if ppid else ""
                child = sysrun(f"pgrep -P {ppid} -a 2>/dev/null").strip() if ppid else ""
                if child:
                    unsub.append({"agent": agent, "window": win, "dangling": dangling, "proc": child[:60]})
                else:
                    dead.append({"agent": agent, "window": win, "dangling": dangling, "pane_proc": proc or "shell"})
    dims["unsubmitted_input"] = unsub
    dims["dead_windows"] = dead
    if unsub or dead:
        entry["level"] = "warn"

    # cpu vs gpu: running encoder processes (libx264/x265 = CPU; h264_vaapi = GPU).
    ps = sysrun("ps -eo args --no-headers")
    enc_cpu = [l for l in ps.splitlines() if re.search(r"ffmpeg.*-c:v (libx264|libx265|mpeg4|libvpx)", l)]
    enc_gpu = [l for l in ps.splitlines() if re.search(r"ffmpeg.*(h264_vaapi|h265_vaapi)", l)]
    wf_cpu = len([l for l in ps.splitlines() if "wf-recorder" in l and "libx264" in l])
    dims["encoders_cpu"] = len(enc_cpu)
    dims["encoders_gpu"] = len(enc_gpu)
    dims["wf_recorder_cpu_capture"] = wf_cpu  # allowed for capture, must be re-encoded after
    if enc_cpu:
        entry["level"] = "warn"
        dims["encoders_cpu_list"] = enc_cpu[:3]

    # chrome CPU-render detection (software GL / swiftshader / no GPU)
    chrome = sysrun("ps -eo args --no-headers | grep -i chrome | grep -vi crashpad")
    cpu_chrome = [l for l in chrome.splitlines() if re.search(r"--disable-gpu|--use-gl=swiftshader|--use-angle=swiftshader|--enable-unsafe-swiftshader", l)]
    dims["chrome_cpu_render"] = len(cpu_chrome)
    if cpu_chrome:
        entry["level"] = "warn"
        dims["chrome_cpu_render_list"] = cpu_chrome[:3]

    # idle/stuck agents from last progress cycle
    st = load(STATE, {"agents": {}})
    bad = [a for a,s in st["agents"].items() if s.get("last_status") in ("IDLE","STUCK")]
    dims["problem_agents"] = bad
    if bad:
        entry["level"] = "warn"

    esc = json.dumps(entry, ensure_ascii=True)
    return esc

def progress_cycle(config, state, now_t, log_lines, anom_lines):
    for agent, cfg in config.get("agents", {}).items():
        st = state["agents"].setdefault(agent, {"next_check_at": 0, "last_status": None, "last_flag": 0})
        if now_t < st.get("next_check_at", 0):
            continue
        interval = max(15, min(int(cfg.get("interval_s", 60)), 600))  # N_check, written by the mind
        st["next_check_at"] = now_t + interval

        agent_dir = cfg.get("dir") or default_agent_dir(agent)
        done = os.path.exists(os.path.join(agent_dir, "done.txt"))
        hb = last_epoch(agent)
        om = output_mtime(agent_dir)
        last_ev = max([x for x in (hb, om) if x] or [0])
        age = now_t - last_ev if last_ev else None

        idle_mult = float(cfg.get("idle_mult", 2))
        stuck_mult = float(cfg.get("stuck_mult", 4))

        if done:
            status, msg = "DONE", "done.txt present"
        elif last_ev == 0:
            status, msg = "NOT_STARTED", "no heartbeat, no output"
        elif age is not None and age > interval * stuck_mult:
            status, msg = "STUCK", f"no evidence for {int(age)}s (>stuck*N={interval*stuck_mult})"
        elif age is not None and age > interval * idle_mult:
            status, msg = "IDLE", f"evidence {int(age)}s old (>idle*N={interval*idle_mult})"
        else:
            status, msg = "WORKING", f"last evidence {age}s ago (N={interval})"

        st.update(last_status=status, last_age=age, last_step=msg)
        log_lines.append(f'[{ts()}] agent={agent} status={status} status_msg="{msg}" age={age} next={interval}')
        if status in ("STUCK", "NOT_STARTED") and now_t - st.get("last_flag", 0) > STUCK_REPEAT_SECS:
            st["last_flag"] = now_t
            anom_lines.append(f'- [{ts()}] **{agent}** → `{status}`: {msg} (N={interval}s)')

def main(force_audit=False):
    os.makedirs(PROG_DIR, exist_ok=True)
    if not os.path.exists(LOGF): open(LOGF, "w").close()
    config = load(CONFIG, {"agents": {}, "time": {}})
    state = load(STATE, {"agents": {}})

    now_t = now()
    log_lines, anom_lines = [], []

    progress_cycle(config, state, now_t, log_lines, anom_lines)
    live_board(config, state, now_t)

    if log_lines:
        with open(LOGF, "a") as f: f.write("\n".join(log_lines) + "\n")
    if anom_lines:
        with open(ANOM, "a") as f: f.write("\n".join(anom_lines) + "\n")
    if config.get("agents"):
        save(STATE, state)

    if force_audit or now_t % AUDIT_SEC < TICK:
        with open(RESLOG, "a") as f:
            f.write(audit(config) + "\n")

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            with open(os.path.join(PM_DIR, "cadence.err"), "a") as f:
                f.write(f"[{ts()}] error: {e}\n")
        time.sleep(TICK)