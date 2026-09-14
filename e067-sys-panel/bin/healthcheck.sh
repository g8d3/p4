#!/usr/bin/env bash
# e067 healthcheck: restart sys-panel if down.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
if curl -sf -m 5 http://127.0.0.1:8326/health >/dev/null; then exit 0; fi
PID=$(ss -tlnp 2>/dev/null | grep ":8326" | grep -oP "pid=\K\d+" | head -1); [ -n "$PID" ] && kill "$PID" 2>/dev/null
sleep 1
cd "$DIR" && nohup python3 "$DIR/app.py" >> server.log 2>&1 &
echo "$(date -Is) restarted" >> server.log
