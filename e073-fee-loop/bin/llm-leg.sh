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

# Budget gate: halt when capped and remaining < $1 (meter needs no API).
CAP=$(grep -m1 '^cap_usd=' ledger/BUDGET 2>/dev/null | cut -d= -f2 || echo unlimited)
if [ "${CAP:-unlimited}" != "unlimited" ] && [ -n "${CAP:-}" ]; then
  SPENT=$(python3 -c "import sqlite3; print(sqlite3.connect('/home/vuos/.local/share/opencode/opencode.db').execute(\"select coalesce(sum(cost),0) from session where datetime(time_updated/1000,'unixepoch') >= datetime('now','-7 days')\").fetchone()[0])" 2>/dev/null || echo 0)
  REM=$(python3 -c "print(float('$CAP') - float('$SPENT'))" 2>/dev/null || echo 0)
  if python3 -c "exit(0 if float('$REM') < 1.0 else 1)"; then echo "leg skipped: budget remaining \$$REM < \$1.00"; exit 0; fi
fi

TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT="runs/leg-$TS-$TASK_ID.md"
SESS="e073-leg-$TS-$TASK_ID"
LEG_START=$(date +%s)
echo "$(date -u +%FT%TZ) LEG $TASK_ID start" >> log/llm-legs.log

timeout 1200 pi --provider opencode-go --model muse-spark-1.3-contributor --session-id "$SESS" --print "
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

# Real per-leg metering: sum usage blocks from this leg's session file(s).
# Falls back to nulls (metered=false) when nothing parseable is found.
read TOK_IN TOK_OUT LEG_COST METERED <<< $(LEG_START="$LEG_START" SESS="$SESS" python3 - <<'EOF'
import os, re, time
start = int(os.environ['LEG_START'])
sess = os.environ['SESS']
pat = re.compile(r'"usage":\{"input":(\d+),"output":(\d+),[^}]*?"total":([0-9.e-]+)\}')
ti = to = 0
cost = 0.0
for dp, _, fns in os.walk(os.path.expanduser('~/.pi/agent/sessions')):
    for fn in fns:
        p = os.path.join(dp, fn)
        try:
            if os.path.getmtime(p) < start:
                continue
            if sess not in fn and sess not in open(p, errors='ignore').read(4000):
                continue
            raw = open(p, errors='ignore').read()
        except OSError:
            continue
        for a, b, c in pat.findall(raw):
            ti += int(a); to += int(b)
            try: cost += float(c)
            except ValueError: pass
print(ti, to, round(cost, 6), str(ti > 0).lower())
EOF
)
python3 - "$TASK_ID" "$TS" "$RC" "$TOK_IN" "$TOK_OUT" "$LEG_COST" "$METERED" <<'EOF' >> ledger/credits.jsonl
import json, sys, datetime
tid, ts, rc = sys.argv[1], sys.argv[2], int(sys.argv[3])
ti, to, cost, metered = sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7] == 'true'
print(json.dumps({"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
  "agent": "dispatcher", "kind": "llm", "model": "muse-spark-1.3-contributor",
  "task": tid, "tokens_in": int(ti) if metered else None,
  "tokens_out": int(to) if metered else None,
  "cost_usd": float(cost) if metered else None, "metered": metered,
  "note": f"leg rc={rc}" + ("" if metered else "; no session usage found")}))
EOF

if [ $RC -eq 0 ] && grep -q "LEG_DONE" "$OUT"; then
  grep -v "^$TASK_ID" LEG_QUEUE > LEG_QUEUE.tmp; mv LEG_QUEUE.tmp LEG_QUEUE
  echo "$(date -u +%FT%TZ) LEG $TASK_ID done, logged" >> log/llm-legs.log
else
  echo "$(date -u +%FT%TZ) LEG $TASK_ID rc=$RC, kept in queue" >> log/llm-legs.log
fi
echo "leg $TASK_ID rc=$RC -> $OUT"
python3 bin/agents-page.py >> log/tick.log 2>&1 || true
