#!/bin/bash
# Stop the results site by exact PID from needs.json pid_file.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PIDF="$(python3 -c "import json,sys;print(json.load(open('$HERE/needs.json'))['pid_file'])")"
if [ -f "$PIDF" ]; then
  PID="$(cat "$PIDF")"
  if kill -0 "$PID" 2>/dev/null; then kill "$PID" && echo "stopped pid $PID"; else echo "pid $PID not running"; fi
  rm -f "$PIDF"
else
  echo "no pid file; nothing to stop"
fi
