#!/bin/bash
# e054 supervisor v2: NOTIFY-ONLY. Watches tracked children listed in agents.registry
# (format: <uuid>|<done-marker>) and ntfy-notifies the user on working<->stopped
# transitions. Does NOT relaunch anything (that is the main session's call).
REG=/home/vuos/code/p4/e054-money-agent/agents.registry
SOCK=/home/vuos/.pi-web/sessiond.sock
CWD=/home/vuos/code/p4
NOTIFY=/home/vuos/code/p4/e000-fundamentals/bin/notify.sh
END=$((SECONDS + 86400))
declare -A last_mod
prev=""
while [ $SECONDS -lt $END ]; do
  working=0
  while IFS='|' read -r id marker; do
    [ -z "$id" ] && continue
    m=$(curl -s --unix-socket "$SOCK" "http://localhost/sessions?cwd=$CWD" | python3 -c "
import json,sys
try:
  rows=json.load(sys.stdin); r=[x for x in rows if x['id']=='$id']
  print(r[0]['modified'] if r else 'gone')
except Exception: print('?')" 2>/dev/null)
    lm="${last_mod[$id]:-}"
    if [ "$m" != "$lm" ]; then working=$((working+1)); fi
    last_mod[$id]="$m"
  done < "$REG"
  st="working"; [ "$working" = "0" ] && st="stopped"
  if [ "$st" != "$prev" ]; then
    if [ "$st" = "stopped" ]; then
      "$NOTIFY" info "e054: agentes visibles detenidos. El main session decide el siguiente paso." -s e054-money-agent
    else
      "$NOTIFY" info "e054: agentes trabajando de nuevo." -s e054-money-agent
    fi
    prev="$st"
  fi
  sleep 60
done
