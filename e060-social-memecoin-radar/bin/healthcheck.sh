#!/bin/bash
# e060 health monitor (cron, every 15 min). Silent on success (conclusions-only
# contract); on failure logs + beats ops bus so errors are never silent. T0 free.
LOG="$HOME/code/p4/e060-social-memecoin-radar/server.log"
OPS="$HOME/code/p4/e062-agent-ops/bin/ops.py"
if curl -s -m 10 -o /dev/null -w "%{http_code}" http://127.0.0.1:8323/health | grep -q "^200$"; then
  exit 0
fi
echo "$(date -u '+%F %T') e060 HEALTH FAIL" >> "$LOG"
python3 "$OPS" beat e060 blocked "health monitor: :8323 /health non-200" 2>>"$LOG" || true
exit 1
