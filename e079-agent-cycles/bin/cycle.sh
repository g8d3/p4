#!/bin/bash
# One agent cycle: start -> (agent does work here) -> finish + bump version.
# Usage: bin/cycle.sh "goal of this version" ["finish notes"]
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=$(python3 -c "import json;print(json.load(open('$DIR/needs.json'))['port'])")
GOAL="${1:-next improvement}"
NOTES="${2:-}"
echo "--- starting cycle: $GOAL"
C=$(curl -s -X POST 127.0.0.1:$PORT/api/cycle/start -H 'Content-Type: application/json' -d "{\"goal\":\"$GOAL\"}")
echo "$C"
ID=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('id',''))" <<<"$C")
[ -z "$ID" ] && echo "start failed (another running?)" && exit 1
echo "--- agent work happens here (ID=$ID) ---"
sleep 1
echo "--- finishing $ID"
curl -s -X POST 127.0.0.1:$PORT/api/cycle/finish -H 'Content-Type: application/json' -d "{\"id\":\"$ID\",\"notes\":\"$NOTES\"}"; echo
echo "--- version now:"; cat "$DIR/version.json"; echo
