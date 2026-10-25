import sys,os,json,time,sqlite3
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
D=os.path.expanduser("~/.config/OpenBot/openbot.db")
AG={"Mango":"9149a12e","Mango Z":"7ac629a7"}
def send(name,msg):
    c=obctl.connect()
    r=obctl.ev(c,obctl.FIRE+"const b=[...document.querySelectorAll('button,a')].find(e=>(e.getAttribute('aria-label')||'').startsWith(%s));if(!b)return 'noagent';fire(b);return 'ok';"%json.dumps(name+", ")))
    time.sleep(2)
    hdr=obctl.ev(c,"return [...document.querySelectorAll('button')].map(b=>b.getAttribute('aria-label')||'').find(x=>x.startsWith('Agent model'))")
    obctl.ev(c,"const e=document.querySelector('[contenteditable=true]');e.focus();return 1;")
    c.send(json.dumps({"id":50,"method":"Input.insertText","params":{"text":msg}}))
    while json.loads(c.recv()).get("id")!=50: pass
    time.sleep(1)
    s=obctl.ev(c,obctl.FIRE+"const b=[...document.querySelectorAll('button')].find(e=>e.getAttribute('aria-label')==='Send message');if(!b)return 'nosend';fire(b);return 'sent';")
    print(r,hdr,s)
def stat(name):
    t="openbot-thread-agent-%%%s%%"%AG[name]
    q=sqlite3.connect("file:%s?mode=ro"%D,uri=True)
    tr=q.execute("select turn_id,status,started_at,completed_at from projection_turns where thread_id like ? order by started_at desc limit 1",(t,)).fetchone()
    print(json.dumps(tr))
def dump(name,turn):
    t="openbot-thread-agent-%%%s%%"%AG[name]
    q=sqlite3.connect("file:%s?mode=ro"%D,uri=True)
    rows=q.execute("select author,item_type,message_json from projection_thread_messages where thread_id like ? and turn_id=? order by created_at,ordinal",(t,turn)).fetchall()
    for a,i,m in rows:
        j=json.loads(m); print("##",a,i,j.get("createdAt")); print((j.get("text") or json.dumps(j)[:1500])[:6000])
    for r in q.execute("select model,occurred_at,tokens_json from agent_usage_records where turn_id=?",(turn,)): print("USAGE",r)
cmd=sys.argv[1]
if cmd=="send": send(sys.argv[2],open(sys.argv[3]).read())
elif cmd=="stat": stat(sys.argv[2])
elif cmd=="dump": dump(sys.argv[2],sys.argv[3])
