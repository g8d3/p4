#!/usr/bin/env python3
"""ask.py <agent name> "message"|@file [--wait [secs]]  - open agent chat by name, send, optionally wait & print reply.
Also: ask.py --stat <agent>   (latest turn as JSON)."""
import sys,os,json,time,sqlite3
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
D=os.path.expanduser("~/.config/OpenBot/openbot.db")
def db(): return sqlite3.connect("file:%s?mode=ro"%D,uri=True)
def thread(name):
    for tid,j in db().execute("select thread_id,agent_json from projection_agents") if False else []: pass
    q=db()
    cols=[r[1] for r in q.execute("pragma table_info(projection_agents)")]
    for row in q.execute("select * from projection_agents"):
        for v in row:
            if isinstance(v,str) and v.startswith("{") and json.loads(v).get("name")==name:
                return json.loads(v)["threadId"]
    sys.exit("no agent named %r"%name)
def last(t):
    return db().execute("select turn_id,status,started_at,completed_at from projection_turns where thread_id=? order by started_at desc limit 1",(t,)).fetchone()
def send(name,msg):
    c=obctl.connect()
    lab=json.dumps(name)
    r=obctl.ev(c,obctl.FIRE+"const n=%s;const b=[...document.querySelectorAll('button,a')].find(e=>{const l=e.getAttribute('aria-label')||'';return l.startsWith(n+', ')||l.startsWith(n+'. ')||l===n;});if(!b)return 'noagent';fire(b);return 'ok';"%lab)
    if r!="ok": sys.exit("agent not in sidebar: "+str(r))
    time.sleep(2)
    obctl.ev(c,"const e=document.querySelector('[contenteditable=true]');e.focus();return 1;")
    c.send(json.dumps({"id":50,"method":"Input.insertText","params":{"text":msg}}))
    while json.loads(c.recv()).get("id")!=50: pass
    time.sleep(1)
    s=obctl.ev(c,obctl.FIRE+"const b=[...document.querySelectorAll('button')].find(e=>e.getAttribute('aria-label')==='Send message');if(!b)return 'nosend';fire(b);return 'sent';")
    if s!="sent": sys.exit("send failed: "+str(s))
def reply(t,turn):
    rows=db().execute("select message_json from projection_thread_messages where thread_id=? and turn_id=? and item_type='final_answer'",(t,turn)).fetchall()
    return "\n".join(json.loads(m[0]).get("text","") for m in rows)
a=sys.argv[1:]
if a[0]=="--stat": print(json.dumps(last(thread(a[1])))); sys.exit()
name,msg=a[0],a[1]
if msg.startswith("@"): msg=open(msg[1:]).read()
import fcntl
_lk=open("/tmp/openbot_ask.lock","w"); fcntl.flock(_lk,fcntl.LOCK_EX)  # one UI driver at a time
try:
    t=thread(name); before=last(t); send(name,msg); print("sent")
finally:
    fcntl.flock(_lk,fcntl.LOCK_UN)
if "--wait" in a:
    i=a.index("--wait"); lim=int(a[i+1]) if len(a)>i+1 else 1800; t0=time.time()
    while time.time()-t0<lim:
        l=last(t)
        if l and l!=before and l[0]!=(before or [None])[0] and l[1]!="running" and l[3]: print(json.dumps(l)); print(reply(t,l[0])); break
        time.sleep(5)
    else: print("timeout")
