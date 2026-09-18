#!/bin/bash
# Append a heartbeat line (liveness proof). Usage: heartbeat.sh <who> [start|end|beat]
# end-events can never read as LIVE on the desk — a finished leg is parked, not running.
WHO="${1:-loop}"
EVENT="${2:-beat}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
printf '{"ts":"%s","who":"%s","event":"%s","host":"%s"}\n' \
  "$(date -u +%FT%TZ)" "$WHO" "$EVENT" "$(hostname)" >> "$DIR/log/heartbeat.jsonl"
echo "heartbeat OK ($WHO/$EVENT)"
