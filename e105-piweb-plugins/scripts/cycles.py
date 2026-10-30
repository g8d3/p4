#!/usr/bin/env python3
"""cycles: what each session-daemon restart interrupted, derived from files that already exist.

A restart drops every working agent and nothing says so afterwards. This builds the ledger
from evidence, with no hooks and no changes to PI WEB:

  * restarts come from systemd (`journalctl -u pi-web-sessiond`, "Started ...");
  * agent activity comes from the session transcripts in ~/.pi/agent/sessions (one .jsonl
    per session, each line stamped).

For every restart it answers: which sessions were active in the window right before it, and
which of them were silent afterwards. "Interrupted" is a claim about evidence, so it is
narrow on purpose: last activity before the restart, nothing after. A session that simply
finished its work an hour earlier is not in that window and never counted.

Output: estado/agent_cycles.json (workspace file, read by the p4.cycles panel)

    python3 scripts/cycles.py                 # analyse, write the ledger
    python3 scripts/cycles.py --since 3d      # look further back
    python3 scripts/cycles.py --table         # print the table, do not write
"""
import argparse
import datetime as dt
import glob
import json
import os
import subprocess
import sys

SESSIONS = os.path.expanduser("~/.pi/agent/sessions")
OUT = os.path.join(os.getcwd(), ".pi-web", "agent_cycles.json")   # --out to change it
PROJECTS = os.path.expanduser("~/.pi-web/projects.json")
PRE_WINDOW_MIN = 45     # how far back "was working when it went down" looks
POST_GRACE_MIN = 10     # how long after a restart a session may stay quiet and still be "resuming"


def boots(since):
    """Session-daemon start times, oldest first."""
    span = since if since.startswith("-") else ("-" + since if since[:-1].isdigit() else since)
    try:
        out = subprocess.run(["journalctl", "--user", "-u", "pi-web-sessiond", "--since", span,
                              "--no-pager", "-o", "short-iso"],
                             capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    stamps = []
    for line in out.splitlines():
        if "Started pi-web-sessiond" in line:
            try:
                stamps.append(dt.datetime.fromisoformat(line.split()[0]).astimezone(dt.timezone.utc))
            except (ValueError, IndexError):
                continue
    return sorted(set(stamps))


def _stamp(obj):
    for key in ("timestamp", "ts", "time"):
        v = obj.get(key)
        if isinstance(v, str):
            try:
                t = dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
                return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)
            except ValueError:
                pass
    return None


def _title_of(row):
    """The first readable line of the conversation, whichever shape the host wrote it in."""
    msg = row.get("message") if isinstance(row, dict) else None
    for blob in (msg, row):
        if not isinstance(blob, dict):
            continue
        c = blob.get("content")
        if isinstance(c, str) and len(c.strip()) > 12:
            return c.strip().replace("\n", " ")[:80]
        if isinstance(c, list):
            for part in c:
                if isinstance(part, dict):
                    txt = part.get("text") or part.get("content")
                    if isinstance(txt, str) and len(txt.strip()) > 12:
                        return txt.strip().replace("\n", " ")[:80]
    return ""


def sessions():
    """(session id, workspace folder, first activity, last activity, tool calls) per transcript."""
    found = []
    for path in glob.glob(os.path.join(SESSIONS, "**", "*.jsonl"), recursive=True):
        first = last = None
        tools = 0
        title = ""
        marks = []
        try:
            with open(path, "rb") as fh:
                size = os.path.getsize(path)
                fh.seek(max(0, size - 400_000))      # the tail is where the recent activity is
                for raw in fh:
                    try:
                        row = json.loads(raw)
                    except Exception:
                        continue
                    t = _stamp(row)
                    if t is not None:
                        first = min(first, t) if first else t
                        last = max(last, t) if last else t
                        marks.append(t)
                    blob = json.dumps(row)[:4000]
                    if '"tool"' in blob or '"toolCall"' in blob:
                        tools += 1
                    if not title:
                        title = _title_of(row)
        except OSError:
            continue
        if last is None:
            continue
        rel = os.path.relpath(path, SESSIONS).split(os.sep)
        marks.sort()
        found.append({"id": os.path.basename(path).replace(".jsonl", ""), "marks": marks[-400:],
                      "folder": rel[0].replace("--", "/").replace("-", "/") if rel else "",
                      "first": first.isoformat() if first else "", "last": last.isoformat(),
                      "tools": tools, "title": title})
    return found


def analyse(boots_list, sess, now):
    cycles = []
    for i, boot in enumerate(boots_list):
        nxt = boots_list[i + 1] if i + 1 < len(boots_list) else now
        pre = boot - dt.timedelta(minutes=PRE_WINDOW_MIN)
        post_until = min(nxt, boot + dt.timedelta(minutes=POST_GRACE_MIN))
        working, resumed, silent = [], [], []
        for s in sess:
            marks = s.get("marks") or []
            if not any(pre <= m < boot for m in marks):
                continue                                  # not active when the daemon went down
            working.append(s)
            if any(m >= boot for m in marks):             # it wrote again after the restart
                resumed.append(s)
            else:
                silent.append(s)
        if not working:
            continue
        cycles.append({
            "boot": boot.isoformat(),
            "next": nxt.isoformat() if nxt else None,
            "working": [{"id": s["id"], "title": s["title"], "last": s["last"], "tools": s["tools"]}
                        for s in working],
            "resumed": [s["id"] for s in resumed],
            "interrupted": [{"id": s["id"], "title": s["title"], "last": s["last"], "tools": s["tools"]}
                            for s in silent],
        })
    return cycles


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="7d")
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--also-projects", action="store_true", default=True,
                    help="also write the ledger into every registered project (panels read inside their workspace)")
    ap.add_argument("--only-out", dest="also_projects", action="store_false")
    a = ap.parse_args(argv)
    now = dt.datetime.now(dt.timezone.utc)
    b = boots(a.since)
    s = sessions()
    cycles = analyse(b, s, now)
    data = {"generated_at": now.isoformat(), "since": a.since, "boots": len(b),
            "sessions_seen": len(s), "windows": {"pre_minutes": PRE_WINDOW_MIN, "grace_minutes": POST_GRACE_MIN},
            "note": "interrupted = active in the window before a restart and quiet after it; "
                    "a session that finished earlier is never counted",
            "cycles": cycles}
    if a.table:
        print(f"boots: {len(b)} | sessions: {len(s)} | cycles with activity: {len(cycles)}")
        for c in cycles:
            print(f"\n  {c['boot'][:19]}  working {len(c['working'])}  resumed {len(c['resumed'])}  "
                  f"interrupted {len(c['interrupted'])}")
            for w in c["interrupted"]:
                print(f"    - {w['title'][:60] or w['id'][:12]}  (last {w['last'][11:19]})")
        return 0
    targets = [a.out]
    if a.also_projects:
        # The facts are machine-wide, but a panel can only read inside its own workspace, and a
        # workspace may be a worktree of another repo. So the same ledger is written into every
        # registered project that has a .pi-web directory to put it in.
        try:
            with open(PROJECTS) as fh:
                for pr in json.load(fh).get("projects") or []:
                    root = pr.get("path")
                    if not root or not os.path.isdir(root):
                        continue
                    roots = [root]
                    # worktrees living inside the project folder are workspaces too, and a
                    # workspace panel reads inside its own workspace
                    try:
                        for child in os.listdir(root):
                            marker = os.path.join(root, child, ".git")
                            if os.path.isfile(marker):
                                roots.append(os.path.join(root, child))
                    except OSError:
                        pass
                    for r in roots:
                        targets.append(os.path.join(r, ".pi-web", "agent_cycles.json"))
        except (OSError, ValueError):
            pass
    written = []
    for target in dict.fromkeys(targets):
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w") as fh:
                json.dump(data, fh, indent=1, ensure_ascii=False)
            written.append(target)
        except OSError:
            continue
    print(f"cycles: {len(cycles)} restarts with active sessions -> {len(written)} ledger(s)")
    for w in written:
        print(f"   {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
