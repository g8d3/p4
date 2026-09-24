#!/usr/bin/env bash
# Serve the desk + data read-only. No deps.
cd "$(dirname "$0")/.."
PORT=${1:-8335}
echo "desk: http://localhost:$PORT/desk.html"
python3 -m http.server "$PORT"
