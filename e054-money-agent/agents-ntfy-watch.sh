#!/bin/bash
# e054 agent-watch: ntfy the user when tracked agents start/stop working.
# Polls the sessiond for children listed in agents.registry (one id per line).
# - all stop working  -> push "ALL AGENTS STOPPED" (once per transition)
# - any starts working -> push "agents working again" (once per transition)
REG=/home/vuos/code/p4/e054-money-agent/agents.registry
SOCK=/home/vuos/.pi-web/sessiond.sock
CWD=/home/vuos/code/p4
NOTIFY=/home/vuos/code/p4/e000-fundamentals/bin/notify.sh
END=$((SECONDS + 86400))
prev=""
while [ $SECONDS -lt $END ]; do
  working=""
  while read -r id; do
    [ -z "$id" ] && continue
    m=$(curl -s --unix-socket "$SOCK" "http://localhost/sessions?cwd=$CWD" | python3 -c "
import json,sys
try:
  rows=json.load(sys.stdin)
  r=[x for x in rows if x['id']=='$id']
  print(r[0]['modified'] if r else 'gone')
except Exception: print('?')")
    case "$m" in gone) sed -i "/^$id$/d" "$REG"; continue;; esac
    last=$(cat /tmp/agent-$id.mod 2>/dev/null)
    if [ "$m" != "$last" ]; then working="$working $id"; fi
    echo "$m" > /tmp/agent-$id.mod
  done < "$REG"
  [ -z "$working" ] && st="idle" || st="working"
  if [ "$st" != "$prev" ]; then
    if [ "$st" = "idle" ]; then
      "$NOTIFY" done "Todos los agentes e054 se han DETENIDO. Estado esperando revision/accion." -s e054-money-agent
    else
      "$NOTIFY" info "Agentes e054 TRABAJANDO de nuevo ($working)." -s e054-money-agent
    fi
    prev="$st"
  fi
  sleep 60
done
