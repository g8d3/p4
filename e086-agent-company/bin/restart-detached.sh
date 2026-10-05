#!/bin/bash
# Detached restarter for /api/ops/restart|restore — outlives the old server.
# $1 = old server PID. Waits for the in-flight response, kills, boots fresh.
sleep 1.5
kill "$1" 2>/dev/null
sleep 2
cd "$(dirname "$0")/.."
nohup python3 server/app.py > server.log 2>&1 &
echo $! > data/server.pid
