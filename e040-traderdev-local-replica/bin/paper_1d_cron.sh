#!/usr/bin/env zsh
# Cron wrapper for the e040 1-day paper-trade monitor (00:15 UTC daily).
set -u
REPO=/home/vuos/code/p4
DIR=$REPO/e040-traderdev-local-replica
LOG=$DIR/output/paper_1d.log

cd "$DIR"
python3 bin/paper_1d.py >> "$LOG" 2>&1

cd "$REPO"
git add -A -- e040-traderdev-local-replica/output/
if git diff --cached --quiet; then
  echo "$(date '+%F %T') no state changes, nothing to push" >> "$LOG"
  exit 0
fi
if git commit -m "e040: auto-update 1d paper trade state ($(date '+%F'))" >> "$LOG" 2>&1; then
  git push origin master >> "$LOG" 2>&1 && echo "$(date '+%F %T') auto-push OK" >> "$LOG" \
    || echo "$(date '+%F %T') auto-push FAILED" >> "$LOG"
else
  echo "$(date '+%F %T') commit FAILED" >> "$LOG"
fi
