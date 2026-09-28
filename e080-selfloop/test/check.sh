#!/bin/bash
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=$(python3 -c "import json;print(json.load(open('$DIR/needs.json'))['port'])")
BASE="http://127.0.0.1:$PORT"
fail(){ echo "FAIL: $1"; exit 1; }
curl -s "$BASE/api/state" | python3 -c "import json,sys;s=json.load(sys.stdin);assert s['version']['version'].startswith('v'),s;assert len(s['answers']['answers'])>=10, 'need 10 self-answers';print('state OK', s['version']['version'], len(s['answers']['answers']), 'answers')" || fail "state"
curl -s "$BASE/" | grep -q "Selfloop" || fail "first paint"
curl -s -X POST "$BASE/api/ask" | grep -q answers || fail "ask"
A=$(curl -s -X POST "$BASE/api/cycle/start" -H 'Content-Type: application/json' -d '{"goal":"check.sh probe"}'); echo "$A" | grep -q '"id"' || echo "(start skipped: $A)"
B=$(curl -s -X POST "$BASE/api/cycle/finish" -H 'Content-Type: application/json' -d '{"notes":"check.sh probe ship"}'); echo "$B" | grep -q version || fail "finish must bump: $B"
curl -s "$BASE/api/usage" | grep -q credits_left || fail "usage"
curl -s "$BASE/api/health" | grep -q alive || fail "health"
echo "PASS"
