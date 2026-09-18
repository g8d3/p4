#!/bin/bash
# Starts the e070 desk on :8327 if not already running (idempotent).
# Read-only over data/ + log/. Logs to log/desk.log.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
if curl -s -m 3 -o /dev/null "http://127.0.0.1:8327/api/state"; then
  echo "desk already up (:8327)"; exit 0
fi
cd "$DIR" || exit 1
setsid nohup python3 bin/desk.py >> log/desk.log 2>&1 < /dev/null &
sleep 1
curl -s -m 5 "http://127.0.0.1:8327/api/state" | head -c 200; echo
