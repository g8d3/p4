#!/bin/bash
# REAL-DATA collector: pulls REAL public no-key facts (crypto spot + USD FX)
# into REAL datasets on schedule. Stdlib only. No keys, no accounts (beyond
# the prod collector node itself), no money, never posts anywhere.
#   bin/collect.sh one      single fetch->ingest->publish tick now
#   bin/collect.sh daemon   background loop every collect_interval_sec (PID file)
#   bin/collect.sh stop     stop the daemon by its exact PID
#   bin/collect.sh status   report daemon + last tick + dataset freshness
# Respect: one small fetch per source per tick, 20s timeouts, <=2 tries with
# backoff; on failure the tick logs fetch-failed and keeps serving cache.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PIDF="$DIR/data/collect.pid"
LOG="$DIR/log/collect.log"
mkdir -p "$DIR/data" "$DIR/log"

tick(){
  python3 - "$DIR" >>"$LOG" 2>&1 <<'EOF'
import sys, json
sys.path.insert(0, sys.argv[1] + "/server")
import collect
print(json.dumps({"tick": collect.collect_tick()}), flush=True)
EOF
}

tick_once(){
  echo "$(date -u +%FT%TZ) collect tick start" >>"$LOG"
  tick
  echo "$(date -u +%FT%TZ) collect tick done" >>"$LOG"
  tail -n 2 "$LOG"
}

daemon(){
  OLD=""
  [ -f "$PIDF" ] && OLD=$(cat "$PIDF" 2>/dev/null)
  if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
    echo "collect daemon already running pid=$OLD"; exit 0
  fi
  INTERVAL=$(python3 -c "import json;print(json.load(open('$DIR/needs.json')).get('collect_interval_sec',1800))")
  setsid nohup bash -c "
    echo \$\$ > '$PIDF'
    while true; do
      python3 - '$DIR' >>'$LOG' 2>&1 <<'PYEOF'
import sys, json
sys.path.insert(0, sys.argv[1] + '/server')
import collect
print(json.dumps({'tick': collect.collect_tick()}), flush=True)
PYEOF
      sleep $INTERVAL
    done
  " >>"$LOG" 2>&1 &
  echo "collect daemon started pid=$!"
  echo "interval: ${INTERVAL}s | log: $LOG | data: /api/public/crypto-spot /api/public/usd-fx"
}

status(){
  if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF" 2>/dev/null)" 2>/dev/null; then
    echo "collect daemon running pid=$(cat "$PIDF")"
  else
    echo "collect daemon stopped"
  fi
  python3 - "$DIR" <<'EOF'
import sys, json, os
d = sys.argv[1]
def tail(p, n=1):
    fp = os.path.join(d, p)
    if not os.path.exists(fp): return []
    lines = open(fp).read().splitlines()
    out = []
    for ln in lines[-n:]:
        try: out.append(json.loads(ln))
        except Exception: pass
    return out
ticks = tail("data/collect.jsonl", 1)
print("last_tick:", json.dumps(ticks[0]) if ticks else "none yet")
try:
    st = json.load(open(os.path.join(d, "data/collect_state.json")))
    print("state:", json.dumps({k: st.get(k) for k in ("at", "ingested_total", "consecutive_failures")}))
except Exception as e:
    print("state: none yet")
EOF
}

case "${1:-one}" in
  one) tick_once;;
  daemon) daemon;;
  stop)
    if [ -f "$PIDF" ]; then
      P=$(cat "$PIDF" 2>/dev/null)
      if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then kill "$P" && rm -f "$PIDF" && echo "collect daemon stopped pid=$P"; else rm -f "$PIDF"; echo "stale pid file removed"; fi
    else echo "not running"; fi;;
  status) status;;
  *) echo "usage: $0 one|daemon|stop|status"; exit 1;;
esac
