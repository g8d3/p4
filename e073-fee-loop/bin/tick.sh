#!/usr/bin/env bash
# Cron-friendly single tick: one paper epoch, lock-guarded. No overlap.
# Crontab: */15 * * * * /home/vuos/code/p4/e073-fee-loop/bin/tick.sh >> log/tick.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
LOCK=/tmp/e073-tick.lock
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK")" 2>/dev/null; then
  echo "$(date -u +%FT%TZ) SKIP previous tick still running"
  exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT
bash bin/epoch.sh
python3 bin/leaderboard.py > LEADERBOARD.md
echo "$(date -u +%FT%TZ) OK epoch done"
