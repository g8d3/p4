#!/bin/bash
# e070 cycle driver: runs loop.sh forever on cadence. No subsessions, no chat.
# Usage: bin/cycle.sh [cadence_seconds, default 1800]  (runs in foreground;
# launch with: setsid nohup bin/cycle.sh >> log/cycle.log 2>&1 &)
# Stop: pkill -f "bin/cycle.sh".
set -u
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" || exit 1
# Single-instance: never two drivers (triplicated 2026-09-18, triple spend).
if pgrep -f "bin/cycle\.sh" | grep -vq "^$$\$"; then
  echo "cycle driver already running, refusing second instance"; exit 0
fi
CADENCE="${1:-1800}"
echo "cycle driver on (every ${CADENCE}s, $(date -u +%FT%TZ))"
while true; do
  bash bin/heartbeat.sh cycle beat >> log/cycle.log 2>&1
  bash bin/loop.sh >> log/cycle.log 2>&1 || echo "$(date -u +%FT%TZ) iteration FAILED rc=$?" >> log/cycle.log
  sleep "$CADENCE"
done
