#!/usr/bin/env bash
# Start / stop / status the Edge Terminal server. Port comes from config.json.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT=$(python3 -c "import json,os;c=json.load(open('server/config.json'));print(os.environ.get(c['server']['envPortOverride'],c['server']['port']))")
LOG=log/server.log
PIDF=log/server.pid
mkdir -p log data

start() {
  if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
    echo "already running pid=$(cat "$PIDF") port=$PORT"
  else
    nohup node server/server.js >>"$LOG" 2>&1 &
    echo $! >"$PIDF"
    for _ in $(seq 1 40); do
      sleep 0.25
      if curl -sf "http://127.0.0.1:$PORT/api/health" >/dev/null; then break; fi
    done
    echo "started pid=$(cat "$PIDF") port=$PORT"
  fi
  report
}
stop() {
  if [ -f "$PIDF" ]; then kill "$(cat "$PIDF")" 2>/dev/null || true; rm -f "$PIDF"; echo stopped; else echo "not running"; fi
}
report() {
  LAN=$(hostname -I 2>/dev/null | awk '{print $1}')
  TS=$(tailscale ip -4 2>/dev/null | head -1 || true)
  echo "Edge Terminal:"
  echo "  http://127.0.0.1:$PORT"
  [ -n "${LAN:-}" ] && echo "  http://$LAN:$PORT   (LAN)"
  [ -n "${TS:-}" ]  && echo "  http://$TS:$PORT   (tailnet)"
}
case "${1:-start}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then echo "running pid=$(cat "$PIDF")"; report; else echo "stopped"; fi ;;
  url) report ;;
  *) echo "usage: $0 [start|stop|restart|status|url]"; exit 1 ;;
esac
