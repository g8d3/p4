#!/bin/bash
# Starts the e070 desk on :8327 if not already running (idempotent).
# Single-instance: never two processes on the port (SO_REUSEADDR would split
# traffic between old and new code). restart = full stop, port-free wait, start.
# Read-only over data/ + log/. Logs to log/desk.log.
# Usage: bin/desk.sh [restart]
DIR="$(cd "$(dirname "$0")/.." && pwd)"

port_free() { ! (ss -ltn 2>/dev/null | grep -q ":8327 ") && ! curl -s -m 2 -o /dev/null "http://127.0.0.1:8327/api/state"; }

if [ "${1:-}" = "restart" ]; then
  pkill -f "[b]in/desk.py" 2>/dev/null
  for _ in $(seq 1 15); do port_free && break; sleep 1; done
  if ! port_free; then echo "desk restart FAILED: :8327 still held"; exit 1; fi
elif curl -s -m 3 -o /dev/null "http://127.0.0.1:8327/api/state"; then
  echo "desk already up (:8327)"; exit 0
else
  # Not responding: make sure no stale twin holds the port, then wait it free.
  pkill -f "[b]in/desk.py" 2>/dev/null
  for _ in $(seq 1 15); do port_free && break; sleep 1; done
fi
cd "$DIR" || exit 1
setsid nohup python3 bin/desk.py >> log/desk.log 2>&1 < /dev/null &
sleep 1
curl -s -m 5 "http://127.0.0.1:8327/api/state" | head -c 200; echo
