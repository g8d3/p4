#!/usr/bin/env bash
# e075 one iteration. Idempotent. PAPER-ONLY in v0. Run from e075-money-loop/.
# This is what the autonomous daemon calls — not a human workflow.
set -e
cd "$(dirname "$0")/.."

if [ -f STOP ]; then
  echo "STOPPED (STOP file present). rm STOP to resume."
  exit 0
fi

TS=$(date -u +%FT%TZ)
ACTOR=${E075_ACTOR:-builder}
mkdir -p log data

# 1. Historical backtest (the self-improvement evidence)
python3 bin/backtest.py
# 2. Read-only wallet snapshot (no keys used)
python3 bin/balance.py || true

OVERALL=$(python3 -c "import json;print(json.load(open('log/backtest.json')).get('overall','ERROR'))" 2>/dev/null || echo "ERROR")
N=$(($(cat data/ledger.jsonl 2>/dev/null | wc -l) + 1))
NOTE="iter $N backtest=$OVERALL paper-only live_enabled=false"

python3 -c "
import json
row={'iter':$N,'ts':'$TS','actor':'$ACTOR','result':'$OVERALL','mode':'PAPER_HISTORY','live_orders':0,'note':'$NOTE','backtest':json.load(open('log/backtest.json')), 'balance':json.load(open('log/balance.json'))}
open('data/ledger.jsonl','a').write(json.dumps(row)+'\n')
print('ledger row', $N, '$OVERALL')
"
python3 -c "
import json, datetime
beat={'ts':'$TS','iter':$N,'actor':'$ACTOR','result':'$OVERALL','mode':'PAPER_HISTORY','live_orders':0,'next_eta':'30 min'}
open('data/heartbeat.json','w').write(json.dumps(beat))
"
python3 bin/render_desk.py
echo "$TS iter $N $OVERALL" >> log/loop.log
echo "iteration $N OK ($OVERALL) — PAPER ONLY, \$0 spent"
