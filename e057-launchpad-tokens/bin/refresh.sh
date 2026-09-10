#!/usr/bin/env bash
# Daily refresh: pull fresh data + rebuild report/charts. Cron-friendly.
cd "$(dirname "$0")/.." || exit 1
echo "=== refresh $(date -Is)" >> refresh.log
python3 bin/fetch.py >> refresh.log 2>&1 && python3 bin/report.py >> refresh.log 2>&1
echo "=== done $(date -Is)" >> refresh.log
