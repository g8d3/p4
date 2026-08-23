#!/usr/bin/env zsh
# Cron wrapper for the e040 TSMR paper monitor (00:30 UTC daily).
set -u
DIR=/home/vuos/code/p4/e040-traderdev-local-replica
cd "$DIR"
python3 bin/paper_tsmr.py >> output/tsmr_paper.log 2>&1
echo "$(date '+%F %T') run complete" >> output/tsmr_paper.log
