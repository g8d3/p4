#!/bin/bash
# One self-pass (heartbeat -> ask -> unstuck -> ship) or never-stopping daemon.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=$(python3 -c "import json;print(json.load(open('$DIR/needs.json'))['port'])")
INT=$(python3 -c "import json;print(json.load(open('$DIR/needs.json')).get('loop_interval_seconds',60))")
BASE="http://127.0.0.1:$PORT"

one() {
  curl -s -X POST "$BASE/api/heartbeat" -H 'Content-Type: application/json' -d '{"by":"loop"}' > /dev/null
  curl -s -X POST "$BASE/api/ask" > /dev/null
  STUCK=$(curl -s "$BASE/api/health" | python3 -c "import json,sys;print('1' if json.load(sys.stdin).get('stuck') else '0')")
  if [ "$STUCK" = "1" ]; then
    echo "[loop] stuck detected -> fixing cause + fact"
    curl -s -X POST "$BASE/api/fix" | head -c 300; echo
  fi
  RUNNING=$(curl -s "$BASE/api/health" | python3 -c "import json,sys;h=json.load(sys.stdin);print(h['running_cycle']['id'] if h.get('running_cycle') else '')")
  if [ -z "$RUNNING" ]; then
    GOAL=$(curl -s "$BASE/api/goals" | python3 -c "import json,sys;g=json.load(sys.stdin);print(g[0]['text'] if g else 'Keep board breathing: smallest visible polish')")
    echo "[loop] starting cycle: $GOAL"
    curl -s -X POST "$BASE/api/cycle/start" -H 'Content-Type: application/json' -d "{\"goal\":$(echo "$GOAL" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')}" | head -c 300; echo
    # smallest work that earns a bump: log nominal loop usage so credits UI moves
    curl -s -X POST "$BASE/api/usage/add" -H 'Content-Type: application/json' -d '{"tokens_in":800,"tokens_out":400,"note":"loop pass"}' > /dev/null
  fi
  # finish what is running (ship a version every pass — never stalls)
  RC=$(curl -s "$BASE/api/health" | python3 -c "import json,sys;h=json.load(sys.stdin);print(h['running_cycle']['goal'] if h.get('running_cycle') else '')")
  if [ -n "$RC" ]; then
    echo "[loop] finishing -> ship version"
    curl -s -X POST "$BASE/api/cycle/finish" -H 'Content-Type: application/json' -d "{\"notes\":$(echo "shipped: $RC" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')}" | head -c 300; echo
  fi
  curl -s "$BASE/api/version"; echo
}

case "${1:-one}" in
  one) one;;
  daemon)
    echo $$ > "$DIR/data/loop.pid"
    echo "[loop] daemon every ${INT}s, pid $$"
    while true; do one >> "$DIR/data/loop.log" 2>&1; sleep "$INT"; done;;
  stop) [ -f "$DIR/data/loop.pid" ] && kill "$(cat "$DIR/data/loop.pid")" && rm "$DIR/data/loop.pid" && echo stopped || echo "not running";;
esac
