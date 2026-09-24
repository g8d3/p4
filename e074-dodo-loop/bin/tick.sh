#!/usr/bin/env bash
# Live ticker: updates heartbeat every 20s so the hub shows WORK without reload.
cd "$(dirname "$0")/.."
while true; do
  TS=$(date -u +%FT%TZ)
  ITER=$(wc -l < data/ledger.jsonl 2>/dev/null || echo 0)
  python3 -c "
import json
try:
  hb=json.load(open('data/heartbeat.json'))
except Exception:
  hb={}
hb['ts']='$TS'
hb['iter']=$ITER
if 'state' not in hb: hb['state']='WORKING'
json.dump(hb, open('data/heartbeat.json','w'))
"
  sleep 20
done
