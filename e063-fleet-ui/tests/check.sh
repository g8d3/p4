#!/bin/bash
# e063 smoke: API shape + write round-trip on a temp DB (never touches prod ops.db).
set -e
cd "$(dirname "$0")/.."
T=$(mktemp -d)
cp /home/vuos/code/p4/e062-agent-ops/ops.db "$T/t.db" 2>/dev/null || sqlite3 "$T/t.db" "CREATE TABLE x(a);"
export E062_DB="$T/t.db" E063_PORT=8399
python3 -c "import sqlite3; c=sqlite3.connect('$T/t.db'); c.execute('DELETE FROM users'); c.execute('DELETE FROM sessions'); c.commit()"
nohup python3 app.py > "$T/s.log" 2>&1 &
SRV=$!
trap "kill $SRV 2>/dev/null; rm -rf $T" EXIT
for i in $(seq 1 30); do curl -sk https://127.0.0.1:8399/api/state >/dev/null 2>&1 && break; sleep 1; done
echo "-- state"; curl -sk https://127.0.0.1:8399/api/state | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'tracks' in d and 'runs' in d and 'proposals' in d, 'shape'; print('tracks:',len(d['tracks']),'runs:',len(d['runs']),'waiting:',len(d['notes'])+len([p for p in d['proposals'] if p['status']=='pending']))"
echo "-- register+note+pause (auth round-trip)"
C=$T/c.txt
curl -sk -c $C -X POST https://127.0.0.1:8399/api/register -H 'Content-Type: application/json' -d '{"name":"tester","pw":"secret12"}' | grep -q '"ok":true'
curl -sk -b $C -X POST https://127.0.0.1:8399/api/note -H 'Content-Type: application/json' -d '{"track":"e062","message":"smoke"}' | grep -q '"ok":true'
curl -sk -b $C -X POST https://127.0.0.1:8399/api/pause -H 'Content-Type: application/json' -d '{"track":"e062"}' | grep -q '"ok":true'
curl -sk -b $C -X POST https://127.0.0.1:8399/api/resume -H 'Content-Type: application/json' -d '{"track":"e062"}' | grep -q '"ok":true'
curl -sk https://127.0.0.1:8399/ | grep -q 'fleet v2'
curl -sk https://127.0.0.1:8399/app.js | grep -q 'vWaiting'
echo "-- version (running==latest, not stale)"; curl -sk https://127.0.0.1:8399/api/version | python3 -c "import json,sys; v=json.load(sys.stdin); assert v['ok'] and v['track']=='e063', v; assert v['running']==v['latest'] and not v['stale'], v; print('version:', v['running'])"
echo ALL PASS
