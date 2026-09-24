#!/usr/bin/env bash
# Decider leg: runs ONLY when LEG_QUEUE is empty. Reads state, queues exactly
# one outward task (or records ASK/KILL in PROGRESS.md). This is what keeps an
# agent working at all times. Throttled by chain.sh via log/last-decide.
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="/home/vuos/.nvm/versions/node/v24.16.0/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p runs log
LOCK=/tmp/e073-decide.lock
exec 9>"$LOCK"
if ! flock -n 9; then echo "decider skipped: already running"; exit 0; fi
[ -s LEG_QUEUE ] && { echo "decider skipped: queue non-empty"; exit 0; }

TS=$(date -u +%Y%m%dT%H%M%SZ)
SESS="e073-decide-$TS"
LEG_START=$(date +%s)
echo "$(date -u +%FT%TZ) LEG decide-$TS start" >> log/llm-legs.log
date -u +%FT%TZ > log/last-decide

timeout 1200 pi --provider opencode-go --model muse-spark-1.3-contributor --session-id "$SESS" --print "
You are the decider in /home/vuos/code/p4/e073-fee-loop. Objective: something
other agents or people want and use, that monetizes. Paper ticks prove nothing.
Read: PROGRESS.md (state, M1 target, kill-list), newest runs/*.md (last proofs),
LEG_QUEUE (must be empty now), ledger/credits.jsonl tail (spend pace).
Rules: output EXACTLY ONE of:
(a) append one task line to LEG_QUEUE: '<id> | <task>. Write runs/<id>.md + PROGRESS.md leg-log line only. End reply with: LEG_DONE task=<id> files=<files> rows=<n>.' The task must end outside the repo (sent, published, used, paid) or be thehard next step toward that. Name the files the worker may write.
(b) a line is dead: append 'KILLED <line>: <reason>' to PROGRESS.md and queue the replacement task instead. A line with 100+ failed tries and zero outside response is dead.
(c) truly blocked: append 'ASK <exact need from human>' to PROGRESS.md and queue nothing.
Never queue another paper tick, survey without a sell step, or a task without done-criteria. Keep it under 9000 output tokens.
" > "runs/decide-$TS.md" 2>&1
RC=$?
read TOK_IN TOK_OUT LEG_COST METERED <<< $(LEG_START="$LEG_START" SESS="$SESS" python3 - <<'EOF'
import os, re
start = int(os.environ['LEG_START']); sess = os.environ['SESS']
pat = re.compile(r'"usage":\{"input":(\d+),"output":(\d+),[^}]*?"total":([0-9.e-]+)\}')
ti = to = 0; cost = 0.0
for dp, _, fns in os.walk(os.path.expanduser('~/.pi/agent/sessions')):
    for fn in fns:
        p = os.path.join(dp, fn)
        try:
            if os.path.getmtime(p) < start: continue
            if sess not in fn and sess not in open(p, errors='ignore').read(4000): continue
            raw = open(p, errors='ignore').read()
        except OSError: continue
        for a, b, c in pat.findall(raw):
            ti += int(a); to += int(b)
            try: cost += float(c)
            except ValueError: pass
print(ti, to, round(cost, 6), str(ti > 0).lower())
EOF
)
python3 - "$TS" "$RC" "$TOK_IN" "$TOK_OUT" "$LEG_COST" "$METERED" <<'EOF' >> ledger/credits.jsonl
import json, sys, datetime
ts, rc = sys.argv[1], int(sys.argv[2])
ti, to, cost, metered = sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6] == 'true'
print(json.dumps({"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
  "agent": "decider", "kind": "llm", "model": "muse-spark-1.3-contributor",
  "task": "decide-" + ts, "tokens_in": int(ti) if metered else None,
  "tokens_out": int(to) if metered else None,
  "cost_usd": float(cost) if metered else None, "metered": metered,
  "note": f"decider rc={rc}"}))
EOF
python3 bin/agents-page.py >> log/tick.log 2>&1 || true
if [ $RC -eq 0 ]; then echo "$(date -u +%FT%TZ) LEG decide-$TS done" >> log/llm-legs.log; else echo "$(date -u +%FT%TZ) LEG decide-$TS rc=$RC" >> log/llm-legs.log; fi
echo "DECIDE rc=$RC"
