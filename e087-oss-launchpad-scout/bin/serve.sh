#!/usr/bin/env bash
# Start server detached (nohup). Port/bind from needs.json.
set -u
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT="$(python3 -c "import json;print(json.load(open('$DIR/needs.json'))['port'])")"
LOG="$DIR/server.log"
nohup python3 "$DIR/server/app.py" >"$LOG" 2>&1 &
echo "e087 serving pid $! port $PORT log $LOG"
