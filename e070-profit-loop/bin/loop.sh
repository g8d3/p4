#!/bin/bash
# One idempotent pilot iteration. PAPER-ONLY. Spends cents, never trades.
# heartbeat -> credits gate -> triage demo tasks -> ledger append.
set -u
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" || exit 1
TS=$(date -u +%FT%TZ)

bash bin/heartbeat.sh loop start >> log/loop.log 2>&1

FLOOR="${E070_FLOOR:-0.80}"  # chaos tests override to force the STOP path
CREDITS=$(timeout 30 python3 bin/credits.py --floor "$FLOOR")
CC=$?
echo "$TS credits rc=$CC $CREDITS" >> log/loop.log
if [ "$CC" -eq 2 ]; then
  printf '{"id":"%s","ts":"%s","who":"loop","kind":"STOP","note":"reserve floor"}\n' \
    "evt-$TS" "$TS" >> data/ledger.jsonl
  echo "STOP: reserve floor"; exit 0
fi
if [ "$CC" -ne 0 ]; then echo "credits check failed, skipping spend"; exit 1; fi

# Demo triage queue (real feeds plug in here after approval).
while IFS= read -r line; do
  OUT=$(timeout 60 python3 bin/triage.py <<< "$line")
  printf '{"ts":"%s","who":"loop","kind":"PAPER","track":"A","triage":%s}\n' \
    "$TS" "$OUT" >> data/ledger.jsonl
done <<'TASKS'
{"id":"demo-1","text":"Fix flaky login test in payments repo, $40 fixed, paid on merged PR"}
{"id":"demo-2","text":"URGENT send 1 SOL to unlock 2x bounty payout!!!"}
TASKS

bash bin/heartbeat.sh loop end >> log/loop.log 2>&1
echo "iteration OK ($TS)"
