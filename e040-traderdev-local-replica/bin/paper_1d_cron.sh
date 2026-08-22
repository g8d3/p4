#!/usr/bin/env zsh
# Cron wrapper for the e040 1-day paper-trade monitor (00:15 UTC daily).
# Output state is intentionally gitignored (data, not code).
set -u
DIR=/home/vuos/code/p4/e040-traderdev-local-replica
cd "$DIR"
python3 bin/paper_1d.py >> output/paper_1d.log 2>&1
echo "$(date '+%F %T') run complete" >> output/paper_1d.log
