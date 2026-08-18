#!/usr/bin/env bash
# progress-monitor shared library
# Determines paths for the progress monitor. Source this from report.sh and monitor.sh.

PM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROG_DIR="${PM_DIR}/progress"          # agents' heartbeats (progress/<agent>.jsonl)
STATE_FILE="${PM_DIR}/monitor-state.json"
CONFIG_FILE="${PM_DIR}/config.json"
LOG_FILE="${PM_DIR}/progress-monitor.log"
ANOM_FILE="${PM_DIR}/anomalies.md"
STUCK_FILE="${PM_DIR}/stuck.md"

now_epoch() { date +%s; }
ts() { date +%Y-%m-%dT%H:%M:%S%z; }

json_get() { python3 -c "import json,sys;d=json.load(open('$1'));print(d$2 if $2 in d else '')" 2>/dev/null; }