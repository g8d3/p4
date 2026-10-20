#!/bin/bash
# FiloEterno forever-loop: builds continuously, guards continuously.
# One process, infinite iterations, heartbeat file for the page.
# Overlap-safe (flock): a second copy exits immediately.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$HERE/data/cycle.lock"
exec 9>"$LOCK"
flock -n 9 || { echo "$(date -u +%FT%TZ) loop already running, exiting"; exit 0; }
set -a
# shellcheck disable=SC1091
. /home/vuos/.secrets/.env 2>/dev/null
set +a
export PATH="$HOME/.foundry/bin:$PATH"
LOG="$HERE/data/cycle.log"

heartbeat() {
  python3 -c "import json,datetime; json.dump({'ts': datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %z'), 'doing': '$1'}, open('$HERE/data/heartbeat.json','w'))"
}

iterate() {
  local NEXT
  NEXT=$(grep -m1 -oP '^-\s*\[next\]\s*\K[A-Za-z0-9][A-Za-z0-9_.-]*' "$HERE/ROADMAP.md" || true)
  if [ -n "$NEXT" ] && [ -f "$HERE/tasks/$NEXT/SPEC.md" ] && [ ! -f "$HERE/tasks/$NEXT/RECEIPT.md" ]; then
    heartbeat "building $NEXT"
    echo "--- building: $NEXT"
    "$HERE/bin/build.py" "$NEXT" 2>&1 | tail -n 8
  else
    heartbeat "guarding (next=$NEXT)"
    echo "--- nothing to build (next=$NEXT)"
  fi
  "$HERE/bin/op.py" 2>&1 | head -n 2
  if [ -z "$(find "$HERE/tasks" -name RECEIPT.md -newer "$HERE/data/exam.stamp" 2>/dev/null)" ]; then
    echo "--- exam: no new builds since last exam, skipping"
  else
    heartbeat "examining auditor"
    echo "--- exam: new build found, running auditor exam"
    "$HERE/bin/exam.py" 2>&1 | tail -n 2
    touch "$HERE/data/exam.stamp"
  fi
  "$HERE/bin/loop.py" probe 2>&1 | tail -n 1
  "$HERE/bin/loop.py" render 2>&1 | tail -n 1
}

if [ "${1:-}" = "--once" ]; then
  { echo "=== $(date -u +%FT%TZ) single iteration"; iterate; echo "=== iteration end"; } >> "$LOG" 2>&1
  exit 0
fi

echo "=== daemon start (continuous)" >> "$LOG" 2>&1
while true; do
  { echo "=== $(date -u +%FT%TZ) iterate"; iterate; echo "=== iteration end"; } >> "$LOG" 2>&1
  sleep 60
done
