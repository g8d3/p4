#!/usr/bin/env python3
"""piweb-restart: restart the PI WEB session daemon without losing work, and prove it.

Design rules (they come from the operator and they are the point of this file):

1. No dumb waits. Whether an agent is busy is read from what the agent itself reports —
   `.pi-web/agent_activity.jsonl`, written by the p4 activity extension (turn_start ... turn_end).
   A stopwatch is never evidence; a timeout may only CANCEL, never authorize.
2. If turning a session off would destroy a turn, we do not guess: we either wait for the turn to
   end (normal path: nothing is interrupted, so nothing needs resuming) or, only with --force, abort
   it and resume it afterwards.
3. Unknown is never idle. A session whose state cannot be read stops the restart unless the operator
   says --allow-unknown, and then the audit records that it was unknown.
4. Every run is audited to `.pi-web/restart_audit.jsonl`, append-only, including the part that is
   easy to skip: whether the resume actually worked (did the session write afterwards?).
5. Times are local with their offset. Durations are measured per phase.

    piweb-restart                 # do it: wait for idle, restart, verify, audit
    piweb-restart --dry           # show the plan, change nothing
    piweb-restart --force         # do not wait: abort busy turns, then resume them
    piweb-restart --report        # last runs from the audit, no action
"""
import argparse
import datetime as dt
import functools
import sys
import glob
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get("PI_WEB_API", "http://127.0.0.1:8504")
MACHINE = os.environ.get("PI_WEB_MACHINE", "local")
SESSIONS_DIR = os.path.expanduser("~/.pi/agent/sessions")
PROJECTS = os.path.expanduser("~/.pi-web/projects.json")
BUSY_EVENTS = {"turn_start", "message_start", "tool_start"}
IDLE_EVENTS = {"turn_end", "session_shutdown"}
RESUME_TEXT = (
    "The PI WEB session daemon was restarted and interrupted your work. "
    "Check what you had in flight (files, todos, running processes) and continue exactly there. "
    "If you had already finished, say so in one line and stop."
)


# --------------------------------------------------------------------- time

def now_local():
    """ISO-8601 with the local offset: a bare UTC stamp is what read as 04:41 for a 23:41 restart."""
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def fmt_local(iso):
    try:
        t = dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.astimezone()
        return t.astimezone().isoformat(timespec="seconds")
    except Exception:
        return str(iso)


# ---------------------------------------------------------------------- api

def api(path, payload=None, timeout=15):
    url = f"{API}/api/machines/{MACHINE}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET",
                                 headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8", "replace")
    return json.loads(body) if body.strip().startswith(("{", "[")) else {}


def daemon_sessions(cwd):
    try:
        rows = api(f"/sessions?cwd={urllib.parse.quote(cwd)}", timeout=8)
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


def daemon_ready(cwd):
    """Only the session daemon answering proves a resume can land; the web answers without it."""
    try:
        return isinstance(api(f"/sessions?cwd={urllib.parse.quote(cwd)}", timeout=5), list)
    except Exception:
        return False


def daemon_started_at():
    try:
        out = subprocess.run(["systemctl", "--user", "show", "pi-web-sessiond", "-p", "ActiveEnterTimestamp"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        return out.split("=", 1)[-1]
    except (OSError, subprocess.SubprocessError):
        return ""


def wait_ready(cwd, seconds):
    t0 = time.time()
    while time.time() - t0 < seconds:
        if daemon_ready(cwd):
            return True, int((time.time() - t0) * 1000)
        time.sleep(0.2)
    return False, int((time.time() - t0) * 1000)


# ------------------------------------------------------- what is really happening

def activity_file(cwd=None):
    """Machine-wide: a daemon restart is machine-wide, so the state must be too."""
    return os.path.join(os.environ.get("PI_WEB_DATA_DIR") or os.path.expanduser("~/.pi-web"),
                        "agent_activity.jsonl")


def activity(cwd):
    """session -> {'state': busy|idle, 'since': iso, 'last': event, 'evidence': str}."""
    out = {}
    path = activity_file(cwd)
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                sid = row.get("session") or ""
                if not sid:
                    continue
                ev = row.get("event") or ""
                state = "busy" if ev in BUSY_EVENTS else ("idle" if ev in IDLE_EVENTS else None)
                prev = out.get(sid) or {}
                out[sid] = {"state": state or prev.get("state") or "idle",
                            "since": row.get("at"), "last": ev, "evidence": "activity file"}
    except FileNotFoundError:
        return {}
    return out


def transcript_for(cwd, sid):
    hits = glob.glob(os.path.join(SESSIONS_DIR, f"*{cwd.rstrip('/').replace('/', '-')}--", f"*{sid}*.jsonl"))
    return hits[0] if hits else None


def candidates(cwd, window_seconds):
    """Every session on the machine that could be hurt by a restart, across all workspaces.

    Scope matters: the daemon serves every project, so a plan that only looks at one cwd declares
    "nothing to protect" and then interrupts everything else (that happened on 2026-10-30).
    """
    cutoff = time.time() - window_seconds
    out = {}
    for sid, info in activity(cwd).items():
        try:
            t = dt.datetime.fromisoformat(str(info.get("since")).replace("Z", "+00:00")).timestamp()
        except Exception:
            t = 0
        if t >= cutoff:
            out[sid] = {"id": sid, "state": info["state"], "since": info.get("since"),
                        "last": info.get("last"), "evidence": info.get("evidence"), "path": ""}
    # sessions the daemon knows for this workspace and that are still recent, so a session with no
    # activity line is reported as unknown instead of silently ignored
    for s in daemon_sessions(cwd):
        path = s.get("path") or ""
        try:
            mtime = os.path.getmtime(path) if path and os.path.exists(path) else 0
        except OSError:
            mtime = 0
        if mtime >= cutoff and s["id"] not in out:
            out[s["id"]] = {"id": s["id"], "state": None, "since": None, "last": None,
                            "evidence": "daemon session, no activity line", "path": path}
    return list(out.values())


def classify(cwd, cands):
    rows = []
    for c in cands:
        state = c.get("state") or "unknown"
        evidence = (f"{c['evidence']}: {c['last']} at {fmt_local(c['since'])}" if c.get("last")
                    else (c.get("evidence") or "no evidence"))
        rows.append({**c, "state": state, "evidence": evidence})
    return rows


# ------------------------------------------------------------------- restart

def restart_unit(override=None):
    return override or "pi-web-sessiond (systemd --user)"


def scope_guard(override):
    """Refuse to restart the default unit while talking to a different instance's API."""
    api_default = API.rstrip("/").endswith(":8504") or API.rstrip("/").endswith("8504")
    if not override and not api_default:
        return ("REFUSING: the API points at {a} but the restart would hit the real unit "
                "pi-web-sessiond. Pass --restart-command for that instance.".format(a=API))
    return None


def do_restart(dry, override=None):
    """Always from a detached unit: a restart must not be a child of the process it kills."""
    if override:
        if dry:
            return override
        subprocess.run(override, shell=True, check=True)
        return override
    unit = f"piweb-restart-{int(time.time())}"
    cmd = ["systemd-run", "--user", "--collect", f"--unit={unit}", "--on-active=1",
           "systemctl", "--user", "restart", "pi-web-sessiond"]
    if dry:
        return " ".join(cmd)
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return unit


def abort_session(cwd, sid):
    try:
        api(f"/sessions/{sid}/abort", {"cwd": cwd}, timeout=10)
        return True, "aborted"
    except urllib.error.HTTPError as e:
        return False, f"abort HTTP {e.code}"
    except Exception as e:
        return False, f"abort failed: {e}"


def resume_session(cwd, sid):
    """One prompt, retried only on transport readiness. 200 does not mean it worked."""
    tries = 0
    while tries < 8:
        try:
            api(f"/sessions/{sid}/prompt", {"cwd": cwd, "text": RESUME_TEXT}, timeout=20)
            return True, f"prompt accepted after {tries} retr{'y' if tries == 1 else 'ies'}"
        except urllib.error.HTTPError as e:
            if e.code not in (502, 503, 504):
                return False, f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:100]}"
            tries += 1
            time.sleep(0.8)
        except Exception as e:
            return False, f"{e}"
    return False, "daemon never became reachable for this session"


def wrote_after(path, ts):
    try:
        return os.path.getmtime(path) >= ts
    except OSError:
        return False


# --------------------------------------------------------------------- audit

def audit_targets(cwd):
    """The record must exist where a panel can read it: the machine, the workspace, every project."""
    targets = [os.path.join(os.environ.get("PI_WEB_DATA_DIR") or os.path.expanduser("~/.pi-web"),
                            "restart_audit.jsonl"),
               os.path.join(cwd, ".pi-web", "restart_audit.jsonl")]
    try:
        with open(PROJECTS) as fh:
            for pr in json.load(fh).get("projects") or []:
                root = pr.get("path")
                if not root or not os.path.isdir(root):
                    continue
                targets.append(os.path.join(root, ".pi-web", "restart_audit.jsonl"))
                for child in os.listdir(root):
                    if os.path.isfile(os.path.join(root, child, ".git")):
                        targets.append(os.path.join(root, child, ".pi-web", "restart_audit.jsonl"))
    except (OSError, ValueError):
        pass
    return list(dict.fromkeys(targets))


def write_audit(cwd, record):
    line = json.dumps(record, ensure_ascii=False) + "\n"
    for target in audit_targets(cwd):
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "a") as fh:
                fh.write(line)
        except OSError:
            continue


def read_audit(path, limit=20):
    rows = []
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except FileNotFoundError:
        return []
    return rows[-limit:]


# ---------------------------------------------------------------------- main

def plan(cwd, a):
    t_start = time.time()
    phases = {}
    cands = candidates(cwd, a.active_window)
    t = time.time()
    rows = classify(cwd, cands)
    phases["classify"] = int((time.time() - t) * 1000)
    busy = [r for r in rows if r["state"] == "busy"]
    unknown = [r for r in rows if r["state"] == "unknown"]
    print(f"workspace  {cwd}")
    print(f"sessions   {len(rows)} recently active "
          f"({len(busy)} busy, {len(rows) - len(busy) - len(unknown)} idle, {len(unknown)} unknown)")
    for r in rows:
        print(f"  - {r['id'][:12]}  {r['state']:<7} {r['evidence']}")
    return rows, busy, unknown, phases, t_start


def main(argv=None):
    print = functools.partial(__builtins__["print"] if isinstance(__builtins__, dict) else __builtins__.print,
                              flush=True)
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--dry", action="store_true", help="show the plan, change nothing")
    ap.add_argument("--force", action="store_true", help="do not wait: abort busy turns, then resume them")
    ap.add_argument("--allow-unknown", action="store_true", help="restart even when a session's state is unreadable")
    ap.add_argument("--report", action="store_true", help="show the last audited runs and exit")
    ap.add_argument("--cwd", default=os.environ.get("P4_WORKSPACE") or os.getcwd())
    ap.add_argument("--active-window", type=int, default=180, help="only consider sessions active in this many seconds")
    ap.add_argument("--max-wait", type=int, default=120, help="how long to wait for turns to end before cancelling")
    ap.add_argument("--resume-wait", type=int, default=30, help="how long to wait for the daemon socket after the restart")
    ap.add_argument("--restart-command", default="",
                    help="restart something other than the default unit (used to rehearse on an isolated instance)")
    a = ap.parse_args(argv)
    cwd = os.path.abspath(a.cwd)

    if a.report:
        rows = read_audit(os.path.join(cwd, ".pi-web", "restart_audit.jsonl"))
        if not rows:
            print("no audited runs in this workspace")
            return 0
        for r in rows[-8:]:
            print(f"{fmt_local(r.get('started'))}  {r.get('mode'):<7} "
                  f"stopped {len(r.get('stopped') or [])}  resumed {len(r.get('resumed') or [])}  "
                  f"lost {len(r.get('lost') or [])}  {r.get('result')}")
        return 0

    guard = scope_guard(a.restart_command)
    if guard and not a.dry:
        print(guard)
        return 4
    rows, busy, unknown, phases, t_start = plan(cwd, a)
    print(f"restart     would run against {restart_unit(a.restart_command)}")
    if a.dry:
        print(f"\nwould restart: {do_restart(True, a.restart_command)}")
        print(f"busy turns {'would be waited for' if busy and not a.force else ('would be aborted (--force)' if busy else 'none')}")
        print(f"resume: {'those whose turn was cut' if busy or a.force else 'nothing (every turn ended before the restart)'}")
        print("dry run: nothing changed")
        return 0

    if unknown and not a.allow_unknown:
        print(f"\nREFUSING: {len(unknown)} session(s) report no state, and unknown is not idle.")
        print("Load the activity extension in those sessions (pi -e .../activity/activity.js), or pass --allow-unknown.")
        return 3

    # 1) wait for turns to end — a condition, not a duration
    t = time.time()
    waited = 0
    while busy and not a.force:
        if waited >= a.max_wait:
            print(f"\nCANCELLED after {waited}s: turns still running. Nothing was killed.")
            print("Rerun with --force to abort them deliberately (they will be resumed), or wait for them.")
            return 2
        time.sleep(0.25)
        waited = int(time.time() - t)
        rows = classify(cwd, candidates(cwd, a.active_window))
        busy = [r for r in rows if r["state"] == "busy"]
    phases["wait_idle"] = int((time.time() - t) * 1000)

    # 2) if forced, abort deliberately and remember whom to resume
    cut = []
    if a.force and busy:
        t = time.time()
        for r in busy:
            ok, detail = abort_session(cwd, r["id"])
            cut.append({**r, "abort": detail, "ok": ok})
        phases["abort"] = int((time.time() - t) * 1000)

    # 3) restart  (the intent is audited first: a run that dies mid-way must still leave a record)
    started = now_local()
    write_audit(cwd, {"started": started, "mode": "force" if a.force else "wait", "workspace": cwd,
                      "result": "started", "intent": True,
                      "trigger": {"pid": os.getpid(), "host": os.uname().nodename,
                                  "argv": " ".join(sys.argv[1:]) or "(no flags)"},
                      "sessions": rows, "unit_hint": restart_unit(a.restart_command)})
    before = daemon_started_at()
    t = time.time()
    unit = do_restart(False, a.restart_command)
    if a.restart_command:
        # A custom command restarts something systemd cannot identify, so its start stamp would
        # never change: waiting on it was the dumbest wait of all (20 s for nothing). Readiness is
        # what we can verify, and the audit records which of the two we actually got.
        restarted, how = True, "assumed (custom restart command; only readiness verified)"
    else:
        while time.time() - t < a.resume_wait and daemon_started_at() == before:
            time.sleep(0.2)
        restarted = daemon_started_at() != before
        how = "confirmed by the systemd start stamp" if restarted else "NOT CONFIRMED"
    phases["restart"] = int((time.time() - t) * 1000)
    new_started = daemon_started_at()

    # 4) wait for the socket, which is what a resume actually needs
    t = time.time()
    ready, waited_ms = wait_ready(cwd, a.resume_wait) if restarted else (False, 0)
    phases["ready"] = waited_ms
    if not restarted:
        print("\nThe daemon's start stamp did not change: the restart did not happen. Nothing resumed.")

    # 5) resume only what got cut, and verify it worked
    resumed, failed = [], []
    t = time.time()
    for r in cut:
        ok, detail = resume_session(cwd, r["id"])
        (resumed if ok else failed).append({**r, "detail": detail})
    phases["resume"] = int((time.time() - t) * 1000)

    # verification window: give the resumed turns a beat to write, then look at the transcripts
    if resumed:
        time.sleep(2.5)
    lost, verified = [], []
    for r in resumed:
        path = r.get("path") or transcript_for(cwd, r["id"]) or ""
        (verified if path and wrote_after(path, t) else lost).append({**r, "path": path})

    result = "ok" if restarted and not failed and not lost else "failed"
    record = {
        "started": started, "finished": now_local(), "mode": "force" if a.force else "wait",
        "workspace": cwd, "trigger": {"pid": os.getpid(), "host": os.uname().nodename,
                                      "argv": " ".join(sys.argv[1:]) or "(no flags)"},
        "sessions": rows, "stopped": [r["id"] for r in rows],
        "cut": cut, "resumed": resumed, "failed": failed, "lost": lost, "verified": verified,
        "restart": {"unit": unit, "happened": restarted, "confirmed": how,
                    "before": before, "after": new_started, "ready": ready},
        "phases_ms": phases, "total_ms": int((time.time() - t_start) * 1000), "result": result,
    }
    write_audit(cwd, record)

    print(f"\nrestart    {how} ({phases['restart']} ms) · "
          f"socket {'ready' if ready else 'NOT READY'} ({phases['ready']} ms)")
    print(f"stopped    {len(rows)} session(s), {len(cut)} turn(s) cut")
    print(f"resumed    {len(resumed)} accepted · {len(failed)} rejected · "
          f"{len(verified)} confirmed writing afterwards · {len(lost)} lost")
    for r in lost:
        print(f"  LOST {r['id'][:12]}: prompt accepted, no write afterwards")
    print(f"total      {record['total_ms']} ms · audit: {os.path.join(cwd, '.pi-web', 'restart_audit.jsonl')}")
    return 0 if result == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
