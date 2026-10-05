#!/bin/bash
# Start Agent Company OS. No env vars — port comes from needs.json.
cd "$(dirname "$0")/.."
PORT=$(python3 -c "import json;print(json.load(open('needs.json'))['port'])" 2>/dev/null || echo 8361)
DATA=data/server.pid
if [ -f "$DATA" ] && kill -0 "$(cat $DATA)" 2>/dev/null; then echo "already running PID $(cat $DATA)"; exit 0; fi
nohup python3 server/app.py > server.log 2>&1 &
echo $! > "$DATA"
sleep 1
echo "PID $! port $PORT"
echo "LAN: http://$(hostname -I | awk '{print $1}'):$PORT/"
TS=$(tailscale ip -4 2>/dev/null | head -n1); [ -n "$TS" ] && echo "Tailnet: http://$TS:$PORT/"
curl -s "http://127.0.0.1:$PORT/api/health" || tail -n 20 server.log
