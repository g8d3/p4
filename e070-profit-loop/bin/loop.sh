#!/bin/bash
# e070 loop v2: the cycle as a PROGRAM on this machine. No subsessions, no chat.
# One idempotent iteration: heartbeat -> credits gate -> scout scans ($0) ->
# hunter triage of NEW finds only (capped) -> metrics -> heartbeat end.
# PAPER-ONLY. Never touches wallets/keys. Daemon driver: `bin/cycle.sh`.
set -u
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" || exit 1
TS=$(date -u +%FT%TZ)
MAX_TRIAGE_PER_ITER=10

bash bin/heartbeat.sh loop start >> log/loop.log 2>&1

FLOOR="${E070_FLOOR:-0.80}"
CREDITS=$(timeout 30 python3 bin/credits.py --floor "$FLOOR")
CC=$?
echo "$TS credits rc=$CC $CREDITS" >> log/loop.log
if [ "$CC" -eq 2 ]; then
  printf '{"id":"%s","ts":"%s","who":"loop","kind":"STOP","note":"reserve floor"}\n' \
    "evt-$TS" "$TS" >> data/ledger.jsonl
  echo "STOP: reserve floor"; exit 0
fi
if [ "$CC" -ne 0 ]; then echo "credits check failed, skipping spend"; exit 1; fi

# Scout scans: $0 inference, real finds.
timeout 120 python3 bin/watch_v1.py >> log/loop.log 2>&1
timeout 60 python3 bin/trends.py >> log/loop.log 2>&1

# Hunter: triage NEW finds only (in watch.jsonl, url not yet in candidates.jsonl).
NEWQ=$(timeout 60 python3 - "$MAX_TRIAGE_PER_ITER" <<'EOF'
import json, sys
n = int(sys.argv[1])
known = set()
try:
    for l in open('data/candidates.jsonl'):
        try: known.add(json.loads(l).get('evidence_url'))
        except ValueError: pass
except FileNotFoundError: pass
out = []
try:
    for l in open('data/watch.jsonl'):
        try: r = json.loads(l)
        except ValueError: continue
        if r.get('url') and r['url'] not in known and len(out) < n:
            out.append({"id": (r.get('venue') or 'w') + '-' + r['url'][-8:],
                        "text": '%s | %s | %s' % (r.get('title',''), r.get('bounty',''), r['url'])})
except FileNotFoundError: pass
print(json.dumps(out))
EOF
)
echo "$NEWQ" | timeout 120 python3 -c "
import json, subprocess, sys
items = json.load(sys.stdin)
spent = 0.0
for it in items:
    p = subprocess.run(['python3', 'bin/triage.py'], input=json.dumps(it),
                       capture_output=True, text=True, timeout=60)
    try: t = json.loads(p.stdout)
    except ValueError: continue
    v = 'WATCH' if ((t.get('payout') or 0) > 0.4 and (t.get('scam') or 1) < 0.5) else 'SKIP'
    spent += (t.get('cost_usd') or 0)
    with open('data/candidates.jsonl', 'a') as f:
        f.write(json.dumps({'vein': it['id'], 'evidence_url': it['text'].split(' | ')[-1],
            'scores': {'payout_likely': t.get('payout'), 'expected_value_14d': (t.get('value') or 0) / 2},
            'verdict': v}) + '\n')
print('hunter: %d triaged spend=%.6f' % (len(items), spent))
" >> log/loop.log 2>&1

timeout 30 python3 bin/metrics.py >> log/loop.log 2>&1
bash bin/heartbeat.sh loop end >> log/loop.log 2>&1
echo "iteration OK ($TS)"
