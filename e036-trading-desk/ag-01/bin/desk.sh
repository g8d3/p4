#!/usr/bin/env bash
# Start the trading desk server on :8088 (idempotent, background, logged).
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$DIR/../output"
mkdir -p "$OUT"
if pgrep -f "python3 .*bin/desk.py" >/dev/null 2>&1; then
  echo "desk already running: $(pgrep -f 'python3 .*bin/desk.py')"
  exit 0
fi
nohup python3 "$DIR/desk.py" >> "$OUT/desk.log" 2>&1 &
echo "started desk pid=$! log=$OUT/desk.log"
sleep 1
curl -s --max-time 5 http://127.0.0.1:8088/api/data | head -c 200; echo
