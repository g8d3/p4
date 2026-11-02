#!/usr/bin/env bash
# Stop the e107 stack by exact PID (never broad pkill).
set -u
cd "$(dirname "$0")/.."
for name in portal socat superagent; do
  pid="$(cat log/$name.pid 2>/dev/null || true)"
  if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" && echo "stopped $name (pid $pid)" || echo "failed to stop $name (pid $pid)"
  else
    echo "$name not running (pid file: ${pid:-none})"
  fi
  rm -f "log/$name.pid"
done
echo "tailscale mappings kept (they are harmless without backends). Remove with:"
echo "  tailscale serve --https=9445 off; tailscale serve --https=9446 off"
