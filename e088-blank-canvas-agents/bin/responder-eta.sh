#!/bin/bash
# responder-eta: FAST LANE loop (~20 min shift, 5s poll).
# Read-only triage only: answer quick questions in words, route builds to zeta.
# Exits when data/resident.stop exists or after 240 cycles (~20 min).
DIR=/home/vuos/code/p4/e088-blank-canvas-agents
TASKS=$DIR/data/tasks.json
RUNNERS=$DIR/data/runners.json
LOG=$DIR/data/log.jsonl
CYCLES=${1:-240}
n=0
iso() { timeout 10s date -u +%FT%TZ; }
heartbeat() {
  timeout 10s python3 -c "
import json,time
p='$RUNNERS'
try: d=json.load(open(p))
except Exception: d={}
d['eta']={'ts':int(time.time()),'doing':'fast lane: watching (cycle $n)'}
json.dump(d,open(p,'w'),indent=1)
" 2>/dev/null
}
logeta() {
  printf '{"ts":"%s","who":"eta","what":"%s"}\n' "$(iso)" "$1" >> "$LOG"
}
triage() {
  timeout 10s python3 -c "
import json, re, subprocess
T='$TASKS'
try: tasks=json.load(open(T))
except Exception: tasks=[]
changed=False
for t in tasks:
  if t.get('status')!='pending' or t.get('lane') or t.get('result'): continue
  txt=(t.get('text') or '')
  low=txt.lower()
  tid=t.get('id','?')
  # build/change signals -> route to zeta lane
  if re.search(r'build|implement|fix|create|add |cambia|arregla|crea|implementa|deploy|despliega|verifica.*build|game|widget|page|pagina|checkout|payment|pago|refactor|migrat|test gate|gate', low):
    t['lane']='work'; changed=True
    print('ROUTE:'+tid); continue
  # quick: model identity
  if re.search(r'model|modelo|inteligencia artificial|quien eres|who are you|which ai|que modelo| Muse |spark', low):
    t['status']='done'; t['adopted_by']='eta'
    t['result']='answered: Muse Spark, running as responder-eta (fast lane, e088 blank-canvas agents)'
    changed=True; print('ANSWER:'+tid+':model'); continue
  # quick: server/health/status
  if re.search(r'estado|health|server|servidor|funciona|works|up\??|gate|green|arriba|activo|status', low):
    try:
      h=subprocess.run(['curl','-s','--max-time','8','http://127.0.0.1:8770/api/health'],capture_output=True,text=True,timeout=10).stdout
      ok='ok' in h
    except Exception: ok=False
    t['status']='done'; t['adopted_by']='eta'
    t['result']='answered: server :8770 api/health ok='+str(ok).lower()+' (probed live by eta, read-only)'
    changed=True; print('ANSWER:'+tid+':status'); continue
  # quick: inbox/task count
  if re.search(r'inbox|tasks|tareas|pendientes|pending|cola|queue', low):
    pend=sum(1 for x in tasks if x.get('status')=='pending')
    t['status']='done'; t['adopted_by']='eta'
    t['result']='answered: inbox pending='+str(pend)+' at triage time (eta fast lane)'
    changed=True; print('ANSWER:'+tid+':inbox'); continue
  # default: route, stay free
  t['lane']='work'; changed=True; print('ROUTE:'+tid+':default')
if changed:
  json.dump(tasks,open(T,'w'),indent=1,ensure_ascii=False)
" 2>/dev/null
}
logeta "eta fast-lane on shift: registered, poll 5s x $CYCLES"
while [ "$n" -lt "$CYCLES" ]; do
  [ -f "$DIR/data/resident.stop" ] && { logeta "resident.stop present, eta shift end"; break; }
  heartbeat
  OUT=$(triage)
  for line in $OUT; do
    case "$line" in
      ANSWER:*) logeta "answered ${line#ANSWER:} in-words (fast lane)" ;;
      ROUTE:*)  logeta "routed ${line#ROUTE:} lane=work -> zeta (needs build, staying free)" ;;
    esac
  done
  n=$((n+1))
  sleep 5
done
logeta "eta shift complete ($n cycles)"
