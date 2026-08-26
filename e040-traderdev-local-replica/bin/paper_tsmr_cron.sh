#!/usr/bin/env zsh
# Cron wrapper for the e040 TSMR paper monitor (00:30 daily).
# Runs the strategy, then auto-commits output state changes and pushes
# to GitHub. Logs everything to output/tsmr_paper.log.
set -u
REPO=/home/vuos/code/p4
DIR=$REPO/e040-traderdev-local-replica
LOG=$DIR/output/tsmr_paper.log

cd "$DIR"
python3 bin/paper_tsmr.py >> "$LOG" 2>&1

cd "$REPO"
git add -A -- e040-traderdev-local-replica/output/
if git diff --cached --quiet; then
  echo "$(date '+%F %T') no state changes, nothing to push" >> "$LOG"
  exit 0
fi
if git commit -m "e040: auto-update paper trade state ($(date '+%F'))" >> "$LOG" 2>&1; then
  if git push origin master >> "$LOG" 2>&1; then
    echo "$(date '+%F %T') auto-push OK" >> "$LOG"
  else
    echo "$(date '+%F %T') auto-push FAILED" >> "$LOG"
  fi
else
  echo "$(date '+%F %T') commit FAILED" >> "$LOG"
fi
