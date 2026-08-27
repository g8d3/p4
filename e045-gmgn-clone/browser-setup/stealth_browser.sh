#!/usr/bin/env bash
# stealth_browser.sh — start / stop the stealth CDP browser.
#   start [port]   launch headless Chrome + stealth injector + wait for CDP
#   stop           stop the browser and the injector
#   status         print pid + port + whether CDP is up
#   port           print the port in use
set -u
BASE="$(cd "$(dirname "$0")" && pwd)"
CMD="${1:-status}"
PORT="${2:-${PORT:-9222}}"
BIN="${CHROME_BIN:-/home/vuos/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome}"

pinfile() { cat "$BASE/browser.pid" 2>/dev/null || true; }
injectpid() { cat "$BASE/stealth_inject.pid" 2>/dev/null || true; }

case "$CMD" in
  start)
    # launch chrome (writes browser.pid, waits for CDP)
    "$BASE/launch_browser.sh" "$PORT" "${PROFILE:-$BASE/stealth-profile}" || { echo "launch failed"; exit 1; }
    # start stealth injector
    nohup python3 "$BASE/stealth_inject.py" "$PORT" > "$BASE/stealth_inject.log" 2>&1 &
    echo $! > "$BASE/stealth_inject.pid"
    sleep 2
    echo "[stealth_browser] injector pid=$(cat "$BASE/stealth_inject.pid")"
    echo "[stealth_browser] READY: agent-browser connect $PORT"
    ;;
  stop)
    IP="$(injectpid)"; BP="$(pinfile)"
    [ -n "$IP" ] && kill "$IP" 2>/dev/null && echo "stopped injector $IP" || echo "no injector"
    [ -n "$BP" ] && kill "$BP" 2>/dev/null && echo "stopped browser $BP" || echo "no browser pid"
    # kill the process tree of the browser root
    [ -n "$BP" ] && pkill -P "$BP" 2>/dev/null
    rm -f "$BASE/browser.pid" "$BASE/stealth_inject.pid"
    echo "[stealth_browser] stopped"
    ;;
  status)
    BP="$(pinfile)"; IP="$(injectpid)"
    echo "browser pid: ${BP:-none}"
    echo "injector pid: ${IP:-none}"
    if [ -n "$BP" ] && kill -0 "$BP" 2>/dev/null; then
      echo "browser: RUNNING"
    else
      echo "browser: NOT running"
    fi
    if [ -n "$IP" ] && kill -0 "$IP" 2>/dev/null; then
      echo "injector: RUNNING"
    else
      echo "injector: NOT running"
    fi
    printf "CDP: "
    curl -s -m 4 "http://127.0.0.1:$PORT/json/version" 2>/dev/null | grep -o '"Browser": "[^"]*"' || echo "down"
    ;;
  port) echo "$PORT" ;;
  *) echo "usage: $0 {start [port]|stop|status|port}"; exit 2 ;;
esac
