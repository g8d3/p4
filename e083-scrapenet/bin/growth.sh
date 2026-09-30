#!/bin/bash
# Growth-loop scheduler: regenerate queue -> post due item -> log result.
#   bin/growth.sh one      single daily tick now (proves the loop)
#   bin/growth.sh daemon   background loop every growth_interval_sec (PID file)
#   bin/growth.sh stop     stop the daemon by its exact PID
#   bin/growth.sh status   report daemon + last tick
# Survives like loop.sh: setsid/nohup-friendly, PID file, appends to
# log/growth-loop.log. Results land in data/growth.jsonl, would-posts in
# data/outbox.jsonl. Never creates accounts, never posts anywhere when the
# backend is dryrun (default), never spends.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PIDF="$DIR/data/growth.pid"
LOG="$DIR/log/growth-loop.log"
mkdir -p "$DIR/data" "$DIR/log"

tick(){
  python3 - "$DIR" >>"$LOG" 2>&1 <<'EOF'
import sys, json
sys.path.insert(0, sys.argv[1] + "/server")
import app
rec = app.growth_tick()
print(json.dumps({"tick": rec}), flush=True)
EOF
}

tick_once(){
  echo "$(date -u +%FT%TZ) tick start" >>"$LOG"
  tick
  echo "$(date -u +%FT%TZ) tick done" >>"$LOG"
  tail -n 2 "$LOG"
}

daemon(){
  OLD=""
  [ -f "$PIDF" ] && OLD=$(cat "$PIDF" 2>/dev/null)
  if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
    echo "growth daemon already running pid=$OLD"; exit 0
  fi
  INTERVAL=$(python3 -c "import json;print(json.load(open('$DIR/needs.json')).get('growth_interval_sec',86400))")
  # setsid-detached loop: survives the launching shell, one tick per interval.
  setsid nohup bash -c "
    echo \$\$ > '$PIDF'
    while true; do
      python3 - '$DIR' >>'$LOG' 2>&1 <<'PYEOF'
import sys, json
sys.path.insert(0, sys.argv[1] + '/server')
import app
print(json.dumps({'tick': app.growth_tick()}), flush=True)
PYEOF
      sleep $INTERVAL
    done
  " >>"$LOG" 2>&1 &
  echo "growth daemon started pid=$!"
  echo "interval: ${INTERVAL}s | log: $LOG | queue: GET /api/growth/queue"
}

case "${1:-one}" in
  one) tick_once;;
  daemon) daemon;;
  stop)
    P=$(cat "$PIDF" 2>/dev/null)
    if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then kill "$P" && rm -f "$PIDF" && echo "stopped $P"; else echo "not running"; rm -f "$PIDF"; fi;;
  status)
    P=$(cat "$PIDF" 2>/dev/null)
    if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then echo "daemon pid=$P alive"; else echo "daemon not running"; fi
    echo "--- last ticks ---"; tail -n 3 "$DIR/data/growth.jsonl" 2>/dev/null || echo "(no ticks yet)"
    echo "--- outbox ---"; tail -n 2 "$DIR/data/outbox.jsonl" 2>/dev/null || echo "(outbox empty)";;
  *) echo "usage: bin/growth.sh one|daemon|stop|status"; exit 1;;
esac
