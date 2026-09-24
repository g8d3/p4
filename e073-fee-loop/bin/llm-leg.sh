#!/usr/bin/env bash
# One bounded LLM leg: pop one task from LEG_QUEUE, run it via pi --print,
# save transcript, log the spend. Usage: bash bin/llm-leg.sh [task-id]
# Uncapped by SPEND.md, bounded per-leg by timeout + task scope.
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="/home/vuos/.nvm/versions/node/v24.16.0/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p runs log
LOCK=/tmp/e073-llm-leg.lock
exec 9>"$LOCK"
if ! flock -n 9; then echo "leg skipped: another LLM leg running"; exit 0; fi

TASK_ID="${1:-}"
if [ -z "$TASK_ID" ]; then TASK_ID=$(head -1 LEG_QUEUE | cut -d'|' -f1 | tr -d ' '); fi
[ -z "$TASK_ID" ] && { echo "queue empty"; exit 0; }
TASK=$(grep -m1 "^$TASK_ID |" LEG_QUEUE || grep -m1 "^$TASK_ID|" LEG_QUEUE || true)
[ -z "$TASK" ] && { echo "task $TASK_ID not in queue"; exit 1; }

TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT="runs/leg-$TS-$TASK_ID.md"
echo "$(date -u +%FT%TZ) LEG $TASK_ID start" >> log/llm-legs.log

timeout 1200 pi --provider opencode-go --model muse-spark-1.3-contributor --print "
You are a table-tending leg in /home/vuos/code/p4/e073-fee-loop.
Hard rules: read-only except the files named below. No keys/tokens in output.
Never invent numbers: every cell comes from a command you ran (curl/GitHub API) or stays empty.
Table doctrine: one fact per column; stamp checked_at on every row you touch (today 2026-09-24).

YOUR ONE TASK: $TASK

Repo context: AGENTS.md (doctrine), PROGRESS.md (state), SPEND.md (authorization).
When done: (1) write the changed files, (2) append one line to PROGRESS.md leg log,
(3) end your reply with: LEG_DONE task=$TASK_ID files=<files> rows=<n>.
" > "$OUT" 2>&1
RC=$?

COST=""  # pi --print does not emit usage; reconcile via OpenCode dashboard
python3 - "$TASK_ID" "$TS" "$RC" <<'EOF' >> ledger/credits.jsonl
import json, sys, datetime
tid, ts, rc = sys.argv[1], sys.argv[2], int(sys.argv[3])
print(json.dumps({"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
  "agent": "dispatcher", "kind": "llm", "model": "muse-spark-1.3-contributor",
  "task": tid, "tokens_in": None, "tokens_out": None, "cost_usd": None,
  "metered": False, "note": f"leg rc={rc}; reconcile via OpenCode dashboard"}))
EOF

if [ $RC -eq 0 ] && grep -q "LEG_DONE" "$OUT"; then
  grep -v "^$TASK_ID" LEG_QUEUE > LEG_QUEUE.tmp; mv LEG_QUEUE.tmp LEG_QUEUE
  echo "$(date -u +%FT%TZ) LEG $TASK_ID done, logged" >> log/llm-legs.log
else
  echo "$(date -u +%FT%TZ) LEG $TASK_ID rc=$RC, kept in queue" >> log/llm-legs.log
fi
echo "leg $TASK_ID rc=$RC -> $OUT"
