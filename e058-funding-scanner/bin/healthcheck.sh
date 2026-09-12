#!/bin/bash
# e058 health monitor (cron, every 15 min). Silent on success (conclusions-only
# contract); on failure logs + beats ops bus so errors are never silent. T0 free.
LOG="$HOME/code/p4/e058-funding-scanner/server.log"
OPS="$HOME/code/p4/e062-agent-ops/bin/ops.py"
code=$(curl -s -m 10 -o /dev/null -w "%{http_code}" http://127.0.0.1:8320/api/table 2>/dev/null) || code="000"
if [ "$code" = "200" ]; then
  exit 0
fi
echo "$(date -u '+%F %T') e058 HEALTH FAIL (code=$code)" >> "$LOG"
python3 "$OPS" beat e058 blocked "health monitor: :8320 /api/table non-200 ($code)" 2>>"$LOG" || true
exit 1
