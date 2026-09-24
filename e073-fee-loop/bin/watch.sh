#!/usr/bin/env bash
# Independent page refresher: regens agents page + live sessions every 5s,
# even mid-leg (chain ticks block while a leg runs). Lightweight, no API.
# Start: (nohup bin/watch.sh >> log/watch.log 2>&1 &)
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p log
echo $$ > log/watch.pid
while true; do
  [ -f STOP ] && exit 0
  python3 bin/agents-page.py >> log/tick.log 2>&1 || true
  sleep 5
done
