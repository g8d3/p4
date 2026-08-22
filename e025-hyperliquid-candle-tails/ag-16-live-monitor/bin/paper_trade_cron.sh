#!/usr/bin/env zsh
# Cron wrapper for the e025 paper-trade monitor (00:15 UTC daily).
# Runs the strategy, then auto-commits output state changes and pushes
# to GitHub. Logs everything to output/monitor.log.
set -u
REPO=/home/vuos/code/p4
DIR=$REPO/e025-hyperliquid-candle-tails/ag-16-live-monitor
LOG=$DIR/output/monitor.log

cd "$DIR"
python3 bin/paper_trade.py >> "$LOG" 2>&1

cd "$REPO"
git add -A -- e025-hyperliquid-candle-tails/ag-16-live-monitor/output/
if git diff --cached --quiet; then
  echo "$(date '+%F %T') no state changes, nothing to push" >> "$LOG"
  exit 0
fi
if git commit -m "e025: auto-update paper trade state ($(date '+%F'))" >> "$LOG" 2>&1; then
  if git push origin master >> "$LOG" 2>&1; then
    echo "$(date '+%F %T') auto-push OK" >> "$LOG"
  else
    echo "$(date '+%F %T') auto-push FAILED" >> "$LOG"
  fi
else
  echo "$(date '+%F %T') commit FAILED" >> "$LOG"
fi
