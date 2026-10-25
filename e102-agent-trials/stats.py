import sqlite3,json,os,collections,datetime as dt
D=os.path.expanduser("~/.config/OpenBot/openbot.db"); q=sqlite3.connect("file:%s?mode=ro"%D,uri=True)
ag={}
for row in q.execute("select * from projection_agents"):
    for v in row:
        if isinstance(v,str) and v.startswith("{"): j=json.loads(v); ag[j["threadId"]]=j["name"]
P=lambda s:dt.datetime.fromisoformat(s.replace("Z","+00:00"))
for t,name in ag.items():
    if name=="Tester": continue
    print("#####",name)
    for tid,st,s,e in q.execute("select turn_id,status,started_at,completed_at from projection_turns where thread_id=? and started_at>'2026-10-25T15:33' order by started_at",(t,)):
        ms=q.execute("select item_type,message_json from projection_thread_messages where thread_id=? and turn_id=? order by created_at,ordinal",(t,tid)).fetchall()
        c=collections.Counter(i for i,_ in ms)
        u=q.execute("select model,tokens_json from agent_usage_records where turn_id=?",(tid,)).fetchall()
        first=[json.loads(m)["text"][:14] for i,m in ms if i is None or i=="" ][:1]
        fin=[json.loads(m).get("text","") for i,m in ms if i=="final_answer"]
        print("--",first,st,"%.0fs"%((P(e)-P(s)).total_seconds() if e else -1),dict(c),[(m,json.loads(k).get("output")) for m,k in u])
        print("   FINAL:",(" | ".join(fin))[:900].replace("\n"," / "))
