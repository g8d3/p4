#!/usr/bin/env bash
# e062 forever-runner leg: one bounded dispatcher pass, then exit.
# Continuity comes from ops.db state, not session stamina.
# Install (owner decision — burns quota 24/7 + may T1-spend):
#   */30 * * * * /home/vuos/code/p4/e062-agent-ops/bin/runner.sh >> /home/vuos/code/p4/e062-agent-ops/runner.log 2>&1
set -uo pipefail
# Single-leg guard: cron and board buttons share this lock. Second trigger exits loud.
LOCK=/tmp/e062-runner.lock
exec 9>"$LOCK"
if ! flock -n 9; then echo "== runner leg skipped: another leg running =="; exit 0; fi
export PATH="/home/vuos/.nvm/versions/node/v24.16.0/bin:/usr/local/bin:/usr/bin:/bin"
OPS=/home/vuos/code/p4/e062-agent-ops/bin/ops.py
PROMPT=/home/vuos/code/p4/e062-agent-ops/RUNNER_PROMPT.md
DB=/home/vuos/code/p4/e062-agent-ops/ops.db
FOCUS="${E062_FOCUS:-fleet}"
TRIGGER="${E062_TRIGGER:-cron}"
RUN_ID="${E062_RUN_ID:-}"
RUN_START=$(date +%s)
echo "== runner leg $(date -u +%Y%m%dT%H%M%SZ) trigger=$TRIGGER focus=$FOCUS =="
if [ -n "$RUN_ID" ]; then
  python3 - "$DB" "$RUN_ID" "$FOCUS" "$TRIGGER" <<'EOF' 2>/dev/null || true
import sqlite3, sys, time
db, rid, focus, trig = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
c = sqlite3.connect(db)
c.execute("CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY AUTOINCREMENT, started_ts INTEGER, ended_ts INTEGER, scope TEXT, trigger TEXT, status TEXT DEFAULT 'running', summary TEXT DEFAULT '')")
c.execute("UPDATE runs SET started_ts=?, scope=?, trigger=?, status='running' WHERE id=?", (int(time.time()), focus, trig, rid))
c.commit(); c.close()
EOF
else
  RUN_ID=$(python3 - "$DB" "$FOCUS" "$TRIGGER" <<'EOF' 2>/dev/null
import sqlite3, sys, time
db, focus, trig = sys.argv[1], sys.argv[2], sys.argv[3]
c = sqlite3.connect(db)
c.execute("CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY AUTOINCREMENT, started_ts INTEGER, ended_ts INTEGER, scope TEXT, trigger TEXT, status TEXT DEFAULT 'running', summary TEXT DEFAULT '')")
cur = c.execute("INSERT INTO runs(started_ts, scope, trigger, status) VALUES (?,?,?,'running')", (int(time.time()), focus, trig))
print(cur.lastrowid)
c.commit(); c.close()
EOF
)
fi
FOCUS_LINE=""
if [ "$FOCUS" != "fleet" ]; then FOCUS_LINE="--- OWNER ONE-SHOT (board button): focus this leg on $FOCUS (approved proposals still first) ---"; fi
STATE=$(python3 $OPS status 2>&1 | head -40)
ORDERS=$(cat /home/vuos/code/p4/e062-agent-ops/DIRECTIVES.md 2>/dev/null | head -60)
PENDING=$(python3 $OPS proposals 2>&1 | head -20)
STALE=$(python3 $OPS stale 49 2>&1 | head -10)
MODEL_ARGS="${E062_MODEL_ARGS:---provider opencode-go --model muse-spark-1.3-contributor}"
timeout 1500 pi $MODEL_ARGS --print "$(cat $PROMPT)

$FOCUS_LINE

--- OWNER DIRECTIVES (highest authority after hard rules) ---
$ORDERS

--- LIVE OPS STATE ---
$STATE
--- PENDING PROPOSALS (only owner-approved ones are executable) ---
$PENDING
--- STALE TRACKS ---
$STALE" 2>&1 | tail -60
echo "== leg end rc=$? =="
python3 $OPS beat runner ok "leg done" >/dev/null 2>&1 || true
# Harvest leg usage (tokens/tok-s/cost) from this leg's pi session file.
# pi logs per-message usage {totalTokens, cost.total} into
# ~/.pi/agent/sessions/<cwd-slug>/*.jsonl — honest numbers, no estimates.
python3 - "$DB" "${RUN_ID:-0}" "$FOCUS" "$TRIGGER" "$RUN_START" <<'EOF' 2>/dev/null || true
import json, os, sqlite3, sys, time
db = sys.argv[1]
try: rid = int(sys.argv[2])
except Exception: rid = 0
focus, trig, start = sys.argv[3], sys.argv[4], int(sys.argv[5])
now = int(time.time())
tok, cost = 0, 0.0
try:
    root = os.path.expanduser('~/.pi/agent/sessions')
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if not fn.endswith('.jsonl'): continue
            p = os.path.join(dp, fn)
            try:
                if int(os.path.getmtime(p)) < start - 60: continue
            except Exception: continue
            # usage.totalTokens is cumulative per message -> max per file
            mtok, mcost = 0, 0.0
            try:
                with open(p) as f:
                    for line in f:
                        try: o = json.loads(line)
                        except Exception: continue
                        if not isinstance(o, dict): continue
                        for u in (o.get('usage'), (o.get('message') or {}).get('usage') if isinstance(o.get('message'), dict) else None):
                            if isinstance(u, dict) and 'totalTokens' in u:
                                mtok = max(mtok, int(u.get('totalTokens') or 0))
                                try: mcost = max(mcost, float((u.get('cost') or {}).get('total') or 0))
                                except Exception: pass
            except Exception: pass
            tok += mtok; cost += mcost
except Exception: pass
if rid:
    c = sqlite3.connect(db)
    try: c.execute('ALTER TABLE runs ADD COLUMN tokens INTEGER')
    except Exception: pass
    try: c.execute('ALTER TABLE runs ADD COLUMN cost_usd REAL')
    except Exception: pass
    c.execute("UPDATE runs SET ended_ts=?, status='done', summary=?, tokens=?, cost_usd=? WHERE id=?",
              (now, f'leg done (focus={focus} trigger={trig})', tok or None, round(cost, 6) or None, rid))
    c.commit(); c.close()
print(f'run {rid} tokens={tok} cost=${cost:.4f}')
EOF
