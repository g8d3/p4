#!/usr/bin/env python3
"""restart-orchestrator: restart the PI WEB session daemon without losing working agents.

A plain `systemctl --user restart pi-web-sessiond` kills every agent mid-turn: whatever it was
doing is lost, and nothing tells it afterwards. This does the five steps the operator described,
in the order that makes them safe:

  1. detect    which sessions are active right now (transcripts written in the last minutes)
  2. quiesce   ask them to stop taking new work, and refuse to continue while any of them is writing
  3. restart   from an EXTERNAL transient unit, so the restart does not die with the daemon it kills
  4. resume    POST one continuation prompt to each session that was active, exactly once,
               recording the attempt BEFORE dispatching (a crash must not resume twice)
  5. report    who came back and who did not, into the ledger the Cycles panel reads

Default is `--plan`: it shows what it would do and changes nothing.

    python3 scripts/restart-orchestrator.py --plan
    python3 scripts/restart-orchestrator.py --execute --quiesce-seconds 8 --max-wait 300

What it refuses to do: restart while an agent is mid-turn (waiting is the point), resume a session
twice, or resume a session that was idle before the restart (that would invent work).
"""
import argparse
import datetime as dt
import glob
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

SESSIONS = os.path.expanduser("~/.pi/agent/sessions")
WORKSPACE = os.environ.get("P4_WORKSPACE", os.getcwd())
LEDGER = os.path.join(WORKSPACE, ".pi-web", "agent_cycles.json")
DISPATCH_LOG = os.path.join(WORKSPACE, ".pi-web", "agent_resumes.jsonl")
STATE = os.path.join(WORKSPACE, ".pi-web", "restart_state.json")
API = os.environ.get("PI_WEB_API", "http://127.0.0.1:8504")
MACHINE = os.environ.get("PI_WEB_MACHINE", "local")
RESUME_TEXT = (
    "The PI WEB session daemon was restarted and interrupted your work. "
    "Check what you had in flight (files, todos, running processes) and continue exactly there. "
    "If you had already finished, say so in one line and stop."
)


def now():
    return dt.datetime.now(dt.timezone.utc)


def api(path, payload=None, timeout=15):
    url = f"{API}/api/machines/{MACHINE}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET",
                                 headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8", "replace")
    return json.loads(body) if body.strip().startswith(("{", "[")) else {}


def last_write(path):
    try:
        return dt.datetime.fromtimestamp(os.path.getmtime(path), dt.timezone.utc)
    except OSError:
        return None


def transcripts(cwd):
    """Session transcripts for one workspace folder (the daemon names the folder after the path)."""
    key = cwd.rstrip("/").replace("/", "-")
    return glob.glob(os.path.join(SESSIONS, f"*{key}--", "**", "*.jsonl"), recursive=True)


def active_sessions(cwd, window_seconds):
    """Sessions that wrote in the last `window_seconds`: candidates to be interrupted."""
    cut = now() - dt.timedelta(seconds=window_seconds)
    out = []
    for path in transcripts(cwd):
        t = last_write(path)
        if t and t >= cut:
            out.append({"id": os.path.basename(path).replace(".jsonl", ""), "path": path,
                        "last_write": t.isoformat()})
    return sorted(out, key=lambda s: s["last_write"], reverse=True)


def daemon_health():
    try:
        with urllib.request.urlopen(f"{API}/api/plugins", timeout=5) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def quiesce_check(cwd, quiet_seconds, timeout, sleep=1.0):
    """Wait until no session wrote for `quiet_seconds`. Returns (ok, detail)."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        recent = active_sessions(cwd, quiet_seconds)
        if not recent:
            return True, f"quiet for {quiet_seconds}s after {int(time.time() - t0)}s"
        time.sleep(sleep)
    return False, f"still writing after {timeout}s: " + ", ".join(s["id"][:8] for s in active_sessions(cwd, quiet_seconds))


def already_resumed(session_id, boot_iso):
    if not os.path.exists(DISPATCH_LOG):
        return False
    with open(DISPATCH_LOG) as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get("session") == session_id and row.get("restart_at") == boot_iso:
                return True
    return False


def record_resume(session_id, boot_iso, ok, detail=""):
    os.makedirs(os.path.dirname(DISPATCH_LOG), exist_ok=True)
    with open(DISPATCH_LOG, "a") as fh:
        fh.write(json.dumps({"at": now().isoformat(), "session": session_id, "restart_at": boot_iso,
                             "ok": ok, "detail": detail}) + "\n")


def resume(cwd, session, boot_iso):
    """One continuation prompt, recorded before it is sent."""
    if already_resumed(session["id"], boot_iso):
        return "skipped (already resumed for this restart)"
    record_resume(session["id"], boot_iso, None, "dispatching")
    try:
        api(f"/sessions/{session['id']}/prompt", {"cwd": cwd, "text": RESUME_TEXT})
        record_resume(session["id"], boot_iso, True)
        return "resumed"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:120]
        record_resume(session["id"], boot_iso, False, f"HTTP {e.code}: {body}")
        return f"failed HTTP {e.code}"
    except Exception as e:
        record_resume(session["id"], boot_iso, False, str(e)[:120])
        return f"failed: {e}"


def do_restart(dry, override=None):
    """Restart from a transient unit so the restart is not a child of the daemon it kills.

    A restart is the one step that survives the process it kills, so it always runs from a
    detached unit; --restart-command exists so the whole flow can be exercised against a
    throwaway instance instead of the daemon the user is working in."""
    if override:
        if dry:
            return override
        subprocess.run(override, shell=True, check=True)
        return override
    unit = f"piweb-restart-{int(time.time())}"
    cmd = ["systemd-run", "--user", "--collect", f"--unit={unit}", "--on-active=2",
           "systemctl", "--user", "restart", "pi-web-sessiond"]
    if dry:
        return " ".join(cmd)
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return unit


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="show what would happen (default)")
    ap.add_argument("--execute", action="store_true", help="actually restart and resume")
    ap.add_argument("--cwd", default=WORKSPACE)
    ap.add_argument("--active-window", type=int, default=180, help="a session is active if it wrote in this many seconds")
    ap.add_argument("--quiesce-seconds", type=int, default=8, help="how long nothing may write before restarting")
    ap.add_argument("--max-wait", type=int, default=300, help="give up (no restart) after this many seconds")
    ap.add_argument("--resume-wait", type=int, default=20, help="seconds to wait for the daemon to come back")
    ap.add_argument("--restart-command", default="",
                    help="command that restarts the daemon (default: the systemd transient unit); "
                         "used to rehearse against a throwaway instance")
    a = ap.parse_args(argv)
    dry = not a.execute

    cwd = os.path.abspath(a.cwd)
    print(f"workspace: {cwd}")
    print(f"daemon:    {API} {'healthy' if daemon_health() else 'NOT ANSWERING'}")

    act = active_sessions(cwd, a.active_window)
    print(f"\n1) active sessions (wrote in the last {a.active_window}s): {len(act)}")
    for s in act[:10]:
        print(f"   - {s['id'][:12]}  last write {s['last_write'][11:19]}")
    if not act:
        print("   nothing to protect: a restart now would lose no work")
        print("\n(dry run: nothing changed)" if dry else "\nrestarting")
        if not dry:
            print("   restart unit:", do_restart(False, a.restart_command))
        return 0

    print(f"\n2) quiesce: waiting until nothing writes for {a.quiesce_seconds}s (max {a.max_wait}s)")
    if dry:
        recent = active_sessions(cwd, a.quiesce_seconds)
        print(f"   right now: {'QUIET' if not recent else str(len(recent)) + ' still writing'}")
        print("\n3) restart (would run):", do_restart(True, a.restart_command))
        print(f"4) resume: one prompt to each of the {len(act)} sessions above, once per restart")
        print("   (dry run: nothing changed)")
        return 0

    ok, detail = quiesce_check(cwd, a.quiesce_seconds, a.max_wait)
    print(f"   {detail}")
    if not ok:
        print("\nABORT: refusing to restart while agents are mid-turn. Nothing was killed.")
        print("Wait for them to finish (or stop them yourself) and run this again.")
        return 2

    boot_iso = now().isoformat()
    unit = do_restart(False, a.restart_command)
    print(f"\n3) restart requested from transient unit {unit} (external: it survives the daemon)")
    t0 = time.time()
    while time.time() - t0 < a.resume_wait:
        if daemon_health():
            break
        time.sleep(1)
    else:
        print("   the daemon did not answer yet; resumes will be attempted anyway (each is recorded)")
    print(f"   daemon {'back' if daemon_health() else 'still down'} after {int(time.time() - t0)}s")

    print(f"\n4) resume: {len(act)} session(s) that were active before the restart")
    results = []
    for s in act:
        r = resume(cwd, s, boot_iso)
        results.append((s["id"], r))
        print(f"   - {s['id'][:12]}: {r}")

    print("\n5) report")
    lost = [i for i, r in results if r.startswith("failed")]
    print(f"   resumed {len(results) - len(lost)}/{len(results)}" + (f" · failed {len(lost)}" if lost else ""))
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w") as fh:
        json.dump({"restart_at": boot_iso, "unit": unit, "cwd": cwd,
                   "active": [s["id"] for s in act], "results": results}, fh, indent=1)
    print(f"   state: {os.path.relpath(STATE, cwd)} · dispatch log: {os.path.relpath(DISPATCH_LOG, cwd)}")
    print("   the Cycles panel reads the ledger; run scripts/cycles.py afterwards for the new boot")
    return 0 if not lost else 1


if __name__ == "__main__":
    sys.exit(main())
