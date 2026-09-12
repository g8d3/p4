#!/usr/bin/env bash
# e062 forever-runner leg: one bounded dispatcher pass, then exit.
# Continuity comes from ops.db state, not session stamina.
# Install (owner decision — burns quota 24/7 + may T1-spend):
#   */30 * * * * /home/vuos/code/p4/e062-agent-ops/bin/runner.sh >> /home/vuos/code/p4/e062-agent-ops/runner.log 2>&1
set -uo pipefail
OPS=/home/vuos/code/p4/e062-agent-ops/bin/ops.py
PROMPT=/home/vuos/code/p4/e062-agent-ops/RUNNER_PROMPT.md
echo "== runner leg $(date -u +%Y%m%dT%H%M%SZ) =="
STATE=$(python3 $OPS status 2>&1 | head -40)
ORDERS=$(cat /home/vuos/code/p4/e062-agent-ops/DIRECTIVES.md 2>/dev/null | head -60)
PENDING=$(python3 $OPS proposals 2>&1 | head -20)
STALE=$(python3 $OPS stale 49 2>&1 | head -10)
MODEL_ARGS="${E062_MODEL_ARGS:---provider opencode-go --model muse-spark-1.3-contributor}"
timeout 1500 pi $MODEL_ARGS --print "$(cat $PROMPT)

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
