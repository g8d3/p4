#!/usr/bin/env bash
# e076 agent CYCLE: one bounded builder leg per trigger, then exit.
# Persistence = loop/state.json + loop/legs/ logs, not session stamina.
# Manual leg:  ./loop/run.sh
# Scheduled:   */30 * * * * /home/vuos/code/p4/e076-bookmark-product/loop/run.sh >> /home/vuos/code/p4/e076-bookmark-product/loop/runner.log 2>&1
# (cron install = owner decision; project cron is currently PAUSED.)
set -uo pipefail
LOCK=/tmp/e076-runner.lock
exec 9>"$LOCK"
if ! flock -n 9; then echo "== leg skipped: another leg running =="; exit 0; fi
export PATH="/home/vuos/.nvm/versions/node/v24.16.0/bin:/usr/local/bin:/usr/bin:/bin"
EXP=/home/vuos/code/p4/e076-bookmark-product
TASK="${E076_TASK:-$(python3 -c "import json;print(json.load(open('$EXP/loop/state.json')).get('next','ship version stamps'))")}"
N=$(python3 -c "import json;s=json.load(open('$EXP/loop/state.json'));print(len(s.get('legs',[]))+1)")
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "== e076 leg #$N $START task=$TASK =="
mkdir -p "$EXP/loop/legs"
JSONL="$EXP/loop/legs/leg-$N.jsonl"
LOG="$EXP/loop/legs/leg-$N.log"
# Mark leg running + consume unanswered human messages (truthful inbox states)
python3 - "$EXP" "$N" "$START" "$TASK" "$EXP/loop/legs/leg-$N.log" <<'EOF'
import json,sys
exp,n,start,task,logf=sys.argv[1],int(sys.argv[2]),sys.argv[3],sys.argv[4],sys.argv[5]
open(logf,'w').write('OWNER: Working on '+task+'\n')
s=json.load(open(exp+'/loop/state.json'))
import datetime as _dt
now=_dt.datetime.strptime(start,"%Y-%m-%dT%H:%M:%SZ")
for l in s.get('legs',[]):
    if l.get('status')=='running':
        try: age=(now-_dt.datetime.strptime(l.get('started',start),"%Y-%m-%dT%H:%M:%SZ")).total_seconds()
        except Exception: age=9999
        if age>1500:
            l.update({"ended":start,"status":"failed","summary":"watchdog: process gone over 25 min, marked failed honestly"})
s.setdefault('legs',[]).append({"n":n,"started":start,"ended":None,"status":"running",
 "summary":"running…","model":"muse-spark","input_tokens":None,"output_tokens":None,"duration_s":None})
s['last_run']=start;json.dump(s,open(exp+'/loop/state.json','w'),indent=1)
ip=exp+'/ops/inbox.json'
try: ib=json.load(open(ip))
except Exception: ib=[]
for m in ib:
    if m.get('from')=='human' and not m.get('answer') and not m.get('in_leg'):
        m['in_leg']=n
json.dump(ib,open(ip,'w'),indent=1)
st={"cycle":"on-demand","last_leg":n,"last_status":"running","last_summary":"Working on: "+task,
 "next":s.get('next',''),"blocked":s.get('blocked_on_human',[]),
 "version":s.get('version','v0'),"updated":start}
json.dump(st,open(exp+'/ops/status.json','w'),indent=1)
EOF
PROMPT="$(cat $EXP/loop/LEG_PROMPT.md)

--- THIS LEG: #$N, task: $TASK ---

--- STATE ---
$(cat $EXP/loop/state.json)

--- HUMAN GATES (do not ask for these, build around them) ---
$(python3 -c "import json;print('\n'.join(x['id']+': '+x['title'] for x in json.load(open('$EXP/ops/needs.json'))))")

--- INBOX (human messages are pre-marked in_leg=$N; reply to each with specifics, in ENGLISH, by appending {from:leg-$N,text} to ops/inbox.json. Set next focus via \"next\" in loop/state.json.) ---
$(cat $EXP/ops/inbox.json 2>/dev/null || echo '[]')
"
timeout 900 pi --mode json --print "$PROMPT" > "$JSONL" 2>"$LOG.err"
CODE=$?
# Human-readable text log + usage totals from JSONL
python3 - "$JSONL" "$LOG" <<'EOF'
import json,sys
jl,log=sys.argv[1],sys.argv[2]
texts=[];mi=mo=0;models=[]
for line in open(jl,errors='replace'):
    try: d=json.loads(line)
    except Exception: continue
    t=d.get('type')
    if t in ('text','message') and isinstance(d.get('text'),str): texts.append(d['text'])
    msg=d.get('message') or {}
    if isinstance(msg,dict):
        for c in (msg.get('content') or []):
            if isinstance(c,dict) and c.get('type')=='text' and c.get('text'): texts.append(c['text'])
        u=msg.get('usage') or {}
        mi+=u.get('input',0) or 0; mo+=u.get('output',0) or 0
        if msg.get('model'): models.append(msg['model'])
open(log,'w').write('\n'.join(texts)+'\n')
print(json.dumps({"in":mi,"out":mo,"model":models[-1] if models else ""}))
EOF
USAGE=$(python3 - "$JSONL" <<'EOF'
import json,sys
mi=mo=0;models=[]
for line in open(sys.argv[1],errors='replace'):
    try: d=json.loads(line)
    except Exception: continue
    msg=d.get('message') or {}
    if isinstance(msg,dict):
        u=msg.get('usage') or {}
        mi+=u.get('input',0) or 0; mo+=u.get('output',0) or 0
        if msg.get('model'): models.append(msg['model'])
print(json.dumps({"in":mi,"out":mo,"model":models[-1] if models else "muse-spark"}))
EOF
)
SUMMARY=$(grep -m1 '^LEG-SUMMARY:' "$LOG" | sed 's/^LEG-SUMMARY: //' || echo "")
[ -z "$SUMMARY" ] && SUMMARY="leg finished exit=$CODE"
END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
STATUS=ok; [ $CODE -ne 0 ] && STATUS=failed
python3 - "$EXP" "$N" "$START" "$END" "$STATUS" "$SUMMARY" "$USAGE" <<'EOF'
import json,sys,datetime
exp,n,start,end,status,summary,usage=sys.argv[1],int(sys.argv[2]),sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6],json.loads(sys.argv[7])
sp=exp+'/loop/state.json'
s=json.load(open(sp))
a=datetime.datetime.strptime(start,"%Y-%m-%dT%H:%M:%SZ");b=datetime.datetime.strptime(end,"%Y-%m-%dT%H:%M:%SZ")
for l in s.get('legs',[]):
    if l.get('n')==n:
        l.update({"ended":end,"status":status,"summary":summary,"model":usage.get('model',''),
         "input_tokens":usage.get('in'),"output_tokens":usage.get('out'),
         "duration_s":int((b-a).total_seconds())})
s['last_run']=end;json.dump(s,open(sp,'w'),indent=1)
ip=exp+'/ops/inbox.json'
try: ib=json.load(open(ip))
except Exception: ib=[]
for m in ib:
    if m.get('in_leg')==n and not m.get('answer'):
        m['answer']=f"Included in leg #{n}"
json.dump(ib,open(ip,'w'),indent=1)
st={"cycle":"on-demand","last_leg":n,"last_status":status,"last_summary":summary,
 "next":s.get('next',''),"blocked":s.get('blocked_on_human',[]),
 "version":s.get('version','v0'),"updated":end}
json.dump(st,open(exp+'/ops/status.json','w'),indent=1)
EOF
echo "== leg #$N $STATUS: $SUMMARY =="
