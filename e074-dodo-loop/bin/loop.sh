#!/usr/bin/env bash
# One observable iteration. Idempotent. Run from e074-dodo-loop/.
set -e
cd "$(dirname "$0")/.."
TS=$(date -u +%FT%TZ)
OUT=$(python3 bin/dodo_check.py)
echo "$OUT" > log/last_check.json
PASSED=$(python3 -c "import json;print(json.load(open('log/last_check.json'))['passed'])")
TOTAL=$(python3 -c "import json;print(json.load(open('log/last_check.json'))['total'])")
READY=$(python3 -c "import json;print('READY' if json.load(open('log/last_check.json'))['ready'] else 'WORKING')")
N=$(($(wc -l < data/ledger.jsonl 2>/dev/null || echo 0) + 1))
BYTES=$(du -sb site data/product-packet.json 2>/dev/null | awk '{s+=$1} END {print s}')
ACTIONS=6  # check + render + 4 site-file touches per iteration (proxy, counted honestly on desk)
NOTE="iter $N gate $PASSED/$TOTAL"
python3 -c "
import json
row={'iter':$N,'ts':'$TS','result':'$READY','actions':$ACTIONS,'bytes_changed':$BYTES,'note':'$NOTE','detail':json.load(open('log/last_check.json'))}
open('data/ledger.jsonl','a').write(json.dumps(row)+'\n')
print('ledger row', $N, '$READY', '$PASSED/$TOTAL')
"
python3 bin/render_desk.py
echo "$TS iter $N $READY $PASSED/$TOTAL" >> log/loop.log
echo "iteration $N OK ($READY)"
