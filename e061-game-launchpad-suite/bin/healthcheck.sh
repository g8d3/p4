#!/bin/bash
# e061 health monitor (cron, every 15 min). Silent on success (conclusions-only
# contract); on failure logs + beats ops bus so errors are never silent. T0 free.
LOG="$HOME/code/p4/e061-game-launchpad-suite/demo/server.log"
OPS="$HOME/code/p4/e062-agent-ops/bin/ops.py"
if curl -s -m 10 -o /dev/null "$HOME/code/p4/e061-game-launchpad-suite/demo/status.json" 2>/dev/null; then :; fi
code=$(curl -s -m 10 -o /dev/null -w "%{http_code}" http://127.0.0.1:8321/ 2>/dev/null) || code="000"
if [ "$code" = "200" ]; then
  # self-heal version badge: restamp when track HEAD moved since last stamp
  HEAD=$(git -C "$HOME/code/p4" log -1 --format=%h -- e061-game-launchpad-suite ':!e061-game-launchpad-suite/demo/version.json' 2>/dev/null)
  STAMP=$(python3 -c "import json;print(json.load(open('$HOME/code/p4/e061-game-launchpad-suite/demo/version.json')).get('commit',''))" 2>/dev/null)
  if [ -n "$HEAD" ] && [ "$HEAD" != "$STAMP" ]; then
    "$HOME/code/p4/e061-game-launchpad-suite/bin/version.sh" >> "$LOG" 2>&1 || true
  fi
  exit 0
fi
echo "$(date -u '+%F %T') e061 HEALTH FAIL (code=$code)" >> "$LOG"
python3 "$OPS" beat e061 blocked "Your game page went dark, reviving it | tech: health monitor: :8321 root non-200 ($code)" 2>>"$LOG" || true
exit 1
