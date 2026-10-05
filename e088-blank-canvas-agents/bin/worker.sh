#!/bin/bash
# One autonomous builder pass. Usage: bin/worker.sh <agent-name>
# The agent reads the canvas, picks the smallest shippable step, builds it, logs it.
set -e
cd "$(dirname "$0")/.."
WHO="${1:-worker}"
echo "[$WHO] autonomous pass: edit canvas/ directly, then log + iterate. No user questions."
echo "Canvas now:"; find canvas -type f | head -50
echo "Log with: echo '{\"ts\":\"'\"\$(date -u +%FT%TZ)\"'\",\"who\":\"$WHO\",\"what\":\"<did>\"}' >> data/log.jsonl"
