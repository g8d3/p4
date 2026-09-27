#!/usr/bin/env bash
# GPU browser for Edge Terminal.
# agent-browser's own launcher hardcodes --use-gl=swiftshader (CPU). We launch
# Chrome ourselves on the AMD GPU (ANGLE over RADV Vulkan) and attach agent-browser
# to it, so charts render on real GPU silicon.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${EDGE_CDP_PORT:-9444}"
PROF="/tmp/e078-gpu-prof"
SESSION="e078"
URL="${EDGE_URL:-http://127.0.0.1:$(python3 -c "import json,os;c=json.load(open('server/config.json'));print(os.environ.get(c['server']['envPortOverride'],c['server']['port']))")/}"

up() { ss -tlnp 2>/dev/null | grep -q ":$PORT "; }

start() {
  if up; then echo "chrome already up on $PORT"; return; fi
  google-chrome --headless=new --no-sandbox --disable-dev-shm-usage \
    --user-data-dir="$PROF" --remote-debugging-port="$PORT" \
    --no-first-run --no-default-browser-check --disable-extensions \
    --ozone-platform=headless --window-size=1500,950 \
    --use-gl=angle --use-angle=vulkan --enable-features=Vulkan \
    --enable-gpu --ignore-gpu-blocklist --disable-gpu-sandbox \
    about:blank >/tmp/e078-chrome.log 2>&1 &
  for _ in $(seq 1 40); do sleep 0.25; up && break; done
  up || { echo "chrome failed to start"; tail -20 /tmp/e078-chrome.log; exit 1; }
  echo "chrome up on cdp $PORT (angle/vulkan)"
}

verify() {
  agent-browser connect "$PORT" --session "$SESSION" >/dev/null 2>&1 || true
  agent-browser open "http://127.0.0.1:${PORT}-blank" >/dev/null 2>&1 || true
  # a real page is required before eval works, so serve the app itself
  agent-browser open "$URL" --session "$SESSION" >/dev/null
  sleep 1
  R=$(agent-browser eval "window.__glRenderer || 'pending'" --session "$SESSION" 2>/dev/null | tr -d '"' || true)
  echo "WebGL renderer: ${R:-unknown}"
  case "$R" in
    *SwiftShader*|*swiftshader*|*llvmpipe*) echo "FAIL: CPU renderer"; return 1 ;;
    *RADV*|*Radeon*|*AMD*) echo "OK: GPU renderer"; return 0 ;;
    *) echo "UNKNOWN renderer (page may not have loaded)"; return 1 ;;
  esac
}

open_app() {
  agent-browser connect "$PORT" --session "$SESSION" >/dev/null 2>&1 || true
  agent-browser open "$URL" --session "$SESSION"
}

stop() {
  if up; then
    PID=$(ss -tlnp 2>/dev/null | grep ":$PORT " | grep -oP 'pid=\K[0-9]+' | head -1)
    [ -n "${PID:-}" ] && kill "$PID" && echo "chrome $PID stopped"
  else echo "chrome not up"; fi
}

case "${1:-start}" in
  start) start ;;
  open) start; open_app ;;
  verify) start; verify ;;
  stop) stop ;;
  *) echo "usage: $0 [start|open|verify|stop]"; exit 1 ;;
esac
