#!/bin/bash
# e062 health monitor (cron, every 15 min). Silent on success (conclusions-only
# contract); on failure logs + beats ops bus so errors are never silent. T0 free.
LOG="$HOME/code/p4/e062-agent-ops/server.log"
OPS="$HOME/code/p4/e062-agent-ops/bin/ops.py"
code=$(curl -s -m 10 -o /dev/null -w "%{http_code}" http://127.0.0.1:8322/api/board 2>/dev/null) || code="000"
if [ "$code" = "200" ]; then
  exit 0
fi
# restart-race guard: one retry after 10s before crying blocked (2026-09-12:
# 15:00 healthcheck raced a server restart -> false blocked beat)
sleep 10
code=$(curl -s -m 10 -o /dev/null -w "%{http_code}" http://127.0.0.1:8322/api/board 2>/dev/null) || code="000"
if [ "$code" = "200" ]; then
  exit 0
fi
echo "$(date -u '+%F %T') e062 HEALTH FAIL (code=$code)" >> "$LOG"
python3 "$OPS" beat e062 blocked "health monitor: :8322 /api/board non-200 ($code)" 2>>"$LOG" || true
exit 1
