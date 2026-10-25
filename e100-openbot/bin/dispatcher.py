#!/usr/bin/env python3
"""openbot-dispatcher: plain-Python job feeder for OpenBot agents (no LLM).
Queue: coco/queue.jsonl (one job per line: id, agent|'any', text, status, attempts, review).
Idle  = agent's latest turn in OpenBot DB is not 'running' and finished >= IDLE_S ago,
        and no job of ours was sent to it after that turn finished.
DONE  = agent writes 'DONE <id>' in a bin/to_coco.sh message (coco/inbox_to_coco.jsonl).
Coco is woken only for: empty queue for an idle agent (once per idle spell),
a job failing twice, or a done job needing review (push/post/deploy/money).
Crash safety: job is marked 'sent' (atomic write) BEFORE ask.py runs -> at most once.
Usage: dispatcher.py [--once] | --simulate"""
import json, os, re, sqlite3, subprocess, sys, time, tempfile
from datetime import datetime, timezone
ROOT = os.path.expanduser("~/code/p4/e100-openbot")
COCO = os.path.join(ROOT, "coco")
QUEUE, STATE = os.path.join(COCO, "queue.jsonl"), os.path.join(COCO, ".dispatcher_state.json")
LOG, INBOX = os.path.join(COCO, "dispatcher.log"), os.path.join(COCO, "inbox_to_coco.jsonl")
DB = os.path.expanduser("~/.config/OpenBot/openbot.db")
AGENTS = ["Mango", "Mango Z", "Rayo", "Brisa"]   # used only if present in OpenBot
POLL_S, IDLE_S, TIMEOUT_S = 5, 60, 600         # timeout: idle this long after send w/o DONE
REVIEW_RE = re.compile(r"\b(push|post|posts|tweet|deploy|publish|money|pay|payment|trade|buy|sell|wallet)\b", re.I)
INSTR = ("\n\n---\nDispatcher job {id}. Rules: local work only; never post, push, deploy or spend money; "
         "paper trading only; never print secrets. When finished run:\n"
         "bin/to_coco.sh \"{agent}\" \"DONE {id}: <one-line result>\"\n"
         "If you cannot finish, send \"FAIL {id}: <reason>\" instead. If you edit coco/GOAL.md, also append "
         "one line to coco/dispatcher.log: '<ts> GOAL-EDIT <who>: <what changed>'.")

def now(): return time.time()
def ts(): return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
def log(m):
    with open(LOG, "a") as f: f.write(f"{ts()} {m}\n")
def atomic(path, text):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, "w") as f: f.write(text); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)
def load_q():
    if not os.path.exists(QUEUE): return []
    return [json.loads(l) for l in open(QUEUE) if l.strip()]
def save_q(q): atomic(QUEUE, "".join(json.dumps(j, ensure_ascii=False) + "\n" for j in q))
def load_s():
    try: return json.load(open(STATE))
    except Exception: return {"inbox_off": os.path.getsize(INBOX) if os.path.exists(INBOX) else 0, "agents": {}}
def save_s(s): atomic(STATE, json.dumps(s, indent=1))

# ---- real backends (replaced in --simulate) ----
def iso(t): return datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp() if t else None
def agent_status():
    """{name: (busy, last_finished_epoch)} for agents present in OpenBot."""
    q = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); out = {}
    for row in q.execute("select * from projection_agents"):
        for v in row:
            if isinstance(v, str) and v.startswith("{"):
                j = json.loads(v)
                if j.get("name") in AGENTS:
                    r = q.execute("select status,started_at,completed_at from projection_turns where thread_id=? "
                                  "order by started_at desc limit 1", (j["threadId"],)).fetchone()
                    if not r: out[j["name"]] = (False, 0)
                    else: out[j["name"]] = (r[0] == "running" or not r[2], iso(r[2]) or iso(r[1]) or 0)
    return out
def send(agent, text):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "bin/ask.py"), agent, text],
                       capture_output=True, text=True, timeout=120)
    return r.returncode == 0 and "sent" in r.stdout
def wake(msg):
    log("WAKE-COCO " + msg)
    subprocess.run([os.path.join(ROOT, "bin/to_coco.sh"), "dispatcher", msg], capture_output=True, timeout=30)
def read_inbox(s):
    if not os.path.exists(INBOX): return []
    with open(INBOX, "rb") as f:
        f.seek(s["inbox_off"]); data = f.read()
    cut = data.rfind(b"\n") + 1; s["inbox_off"] += cut
    out = []
    for l in data[:cut].decode("utf8", "replace").splitlines():
        try: out.append(json.loads(l))
        except Exception: pass
    return out

B = {"status": agent_status, "send": send, "wake": wake, "inbox": read_inbox, "now": now}

def step(q, s):
    t = B["now"](); changed = False
    for m in B["inbox"](s):
        if m.get("from") == "dispatcher": continue
        for kind, jid, rest in re.findall(r"\b(DONE|FAIL)\s+([\w.-]+):?\s*(.*)", m.get("msg", "")):
            for j in q:
                if j["id"] == jid and j["status"] == "sent":
                    changed = True
                    if kind == "DONE":
                        j["status"] = "done"; j["done_at"] = t
                        log(f"DONE {jid} by {m.get('from')}: {rest[:200]}")
                        if j.get("review") or REVIEW_RE.search(j["text"] + " " + rest):
                            B["wake"](f"REVIEW job {jid} done by {j['sent_to']}: {rest[:300]}")
                    else: fail(j, f"agent said FAIL: {rest[:200]}")
    st = B["status"]()
    for a, (busy, fin) in st.items():
        ag = s["agents"].setdefault(a, {"woke_empty": False})
        if busy: ag["woke_empty"] = False; continue
        mine = [j for j in q if j["status"] == "sent" and j.get("sent_to") == a]
        if mine:   # waiting for DONE; time out if agent idles long after the send
            j = mine[0]
            if fin and fin > j["sent_at"] and t - fin >= TIMEOUT_S: fail(j, "timeout: idle w/o DONE"); changed = True
            continue
        if t - fin < IDLE_S: continue
        job = next((j for j in q if j["status"] == "pending" and j["agent"] in (a, "any")), None)
        if not job:
            if not ag["woke_empty"]:
                ag["woke_empty"] = True; save_s(s)
                B["wake"](f"queue empty for idle agent {a}")
            continue
        ag["woke_empty"] = False
        job.update(status="sent", sent_to=a, sent_at=t); save_q(q); save_s(s)   # commit BEFORE send
        ok = False
        try: ok = B["send"](a, job["text"] + INSTR.format(id=job["id"], agent=a))
        except Exception as e: log(f"send error {job['id']}: {e}")
        log(f"SENT {job['id']} -> {a} ok={ok}")
        if not ok: fail(job, "ask.py send failed")
        changed = True
    if changed: save_q(q)
    save_s(s)

def fail(j, why):
    j["attempts"] = j.get("attempts", 0) + 1
    log(f"FAIL {j['id']} attempt {j['attempts']}: {why}")
    if j["attempts"] >= 2:
        j["status"] = "failed"; B["wake"](f"job {j['id']} failed twice: {why}")
    else: j["status"] = "pending"; j.pop("sent_to", None)

def run(once=False):
    while True:
        try: step(load_q(), load_s())
        except Exception as e: log(f"loop error: {e!r}")
        if once: return
        time.sleep(POLL_S)

def simulate():
    global QUEUE, STATE, LOG, INBOX
    d = tempfile.mkdtemp(); QUEUE, STATE, LOG, INBOX = (os.path.join(d, x) for x in ("q", "s", "log", "in"))
    open(INBOX, "w").close()
    clock = [1000.0]; agents = {"Mango": [False, 900.0], "Mango Z": [True, 0]}
    sent, wakes = [], []
    B.update(now=lambda: clock[0], status=lambda: {k: tuple(v) for k, v in agents.items()},
             send=lambda a, t: sent.append((a, t)) or True, wake=lambda m: wakes.append(m))
    B["inbox"] = read_inbox
    def inbox(frm, msg):
        with open(INBOX, "a") as f: f.write(json.dumps({"from": frm, "msg": msg}) + "\n")
    save_q([{"id": "j1", "agent": "Mango", "text": "task one", "status": "pending"},
            {"id": "j2", "agent": "Mango", "text": "deploy site", "status": "pending"},
            {"id": "j3", "agent": "Mango", "text": "flaky", "status": "pending"}])
    res = []
    def check(name, cond): res.append((name, bool(cond))); print(("PASS " if cond else "FAIL ") + name)
    agents["Mango"] = [False, 970.0]; run(True)           # idle only 30s
    check("idle<60s not dispatched", not sent)
    clock[0] = 1031; run(True)
    check("idle>=60s dispatches top job j1", len(sent) == 1 and "j1" in sent[0][1] and "DONE j1" in sent[0][1])
    check("busy agent untouched", all(a != "Mango Z" for a, _ in sent))
    for _ in range(3): clock[0] += 5; run(True)
    check("no double-send (incl. restart w/ fresh state load)", len(sent) == 1)
    inbox("Mango", "DONE j1: finished"); agents["Mango"] = [False, clock[0]]; clock[0] += 61; run(True)
    q = {j["id"]: j for j in load_q()}
    check("DONE marks done, no wake", q["j1"]["status"] == "done" and not wakes)
    check("next job j2 sent after DONE", len(sent) == 2 and "j2" in sent[1][1])
    inbox("Mango", "DONE j2: deployed"); agents["Mango"] = [False, clock[0]]; clock[0] += 61; run(True)
    check("review job wakes Coco once", len(wakes) == 1 and "REVIEW" in wakes[0])
    check("j3 sent", len(sent) == 3)
    for n in (1, 2):   # j3 fails twice
        inbox("Mango", "FAIL j3: broke"); agents["Mango"] = [False, clock[0]]; clock[0] += 61; run(True)
    q = {j["id"]: j for j in load_q()}
    check("failure twice -> failed + wake", q["j3"]["status"] == "failed" and any("failed twice" in w for w in wakes))
    n = len(wakes); clock[0] += 61; run(True); clock[0] += 5; run(True); clock[0] += 5; run(True)
    E=lambda: sum("queue empty" in w for w in wakes)
    check("empty queue wakes once per idle spell", E() == 1)
    agents["Mango"] = [True, 0]; run(True); agents["Mango"] = [False, clock[0]]; clock[0] += 61; run(True)
    check("new idle spell wakes again", E() == 2)
    print(f"{sum(r for _, r in res)}/{len(res)} passed"); sys.exit(0 if all(r for _, r in res) else 1)

if __name__ == "__main__":
    if "--simulate" in sys.argv: simulate()
    else: run("--once" in sys.argv)
