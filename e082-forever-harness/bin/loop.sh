#!/bin/bash
# One tick (heartbeat -> verify -> compact -> ship micro-goal) or never-stopping daemon.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=$(python3 -c "import json;print(json.load(open('$DIR/needs.json'))['port'])")
INT=$(python3 -c "import json;print(json.load(open('$DIR/needs.json')).get('loop_interval_seconds',60))")
BASE="http://127.0.0.1:$PORT"
TOK=$(python3 -c "import json;print(json.load(open('$DIR/needs.json')).get('TOKEN',''))")
AUTH=(); [ -n "$TOK" ] && AUTH=(-H "Authorization: Bearer $TOK")

one() {
  RUNNING=$(curl -s "$BASE/api/status" | python3 -c "import json,sys;print('1' if json.load(sys.stdin).get('running') else '0')")
  if [ "$RUNNING" != "1" ]; then
    echo "[loop] starting"
    curl -s -X POST "$BASE/api/control/start" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{}' | head -c 200; echo
  fi
  echo "[loop] tick: heartbeat -> verify -> compact -> ship"
  curl -s -X POST "$BASE/api/control/tick" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"by":"loop"}' | head -c 500; echo
  curl -s "$BASE/api/status" | python3 -c "import json,sys;s=json.load(sys.stdin);print('[loop] cycle',s['cycle'],'quality',s['quality'],'budget',s['budget_used'],'/',s['budget_total'],'running',s['running'])"
}

case "${1:-one}" in
  one) one;;
  daemon)
    echo $$ > "$DIR/data/loop.pid"
    echo "[loop] daemon every ${INT}s, pid $$"
    while true; do one >> "$DIR/data/loop.log" 2>&1; sleep "$INT"; done;;
  stop) [ -f "$DIR/data/loop.pid" ] && kill "$(cat "$DIR/data/loop.pid")" && rm "$DIR/data/loop.pid" && echo stopped || echo "not running";;
esac
