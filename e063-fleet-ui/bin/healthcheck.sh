#!/bin/bash
# e063 health monitor (cron, every 15 min). Silent on success; on failure
# logs + beats ops bus so errors are never silent. T0 free.
# NOTE: :8325 serves https (tail cert) like :8322 — plain http always 000.
LOG="$HOME/code/p4/e063-fleet-ui/server.log"
OPS="$HOME/code/p4/e062-agent-ops/bin/ops.py"
code=$(curl -sk -m 10 -o /dev/null -w "%{http_code}" https://127.0.0.1:8325/api/version 2>/dev/null) || code="000"
if [ "$code" = "200" ]; then
  exit 0
fi
# restart-race guard: one retry after 10s before crying blocked
sleep 10
code=$(curl -sk -m 10 -o /dev/null -w "%{http_code}" https://127.0.0.1:8325/api/version 2>/dev/null) || code="000"
if [ "$code" = "200" ]; then
  exit 0
fi
echo "$(date -u '+%F %T') e063 HEALTH FAIL (code=$code)" >> "$LOG"
python3 "$OPS" beat e063 blocked "Your new board is down, retrying | tech: health monitor: :8325 /api/version non-200 ($code)" 2>>"$LOG" || true
exit 1
