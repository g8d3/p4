#!/usr/bin/env bash
# Stop the e107 stack by exact PID (never broad pkill).
set -u
cd "$(dirname "$0")/.."
# port each daemon must free; a pid file can hold a launcher wrapper (npm/npx),
# so verify by port and kill the exact holder read from ss -tlnp (never pkill).
declare -A PORT_OF=( [superagent]=3082 [socat]=8444 [portal]=8091 )
for name in portal socat superagent; do
  pid="$(cat log/$name.pid 2>/dev/null || true)"
  if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" && echo "stopped $name (pid $pid)" || echo "failed to stop $name (pid $pid)"
  else
    echo "$name not running (pid file: ${pid:-none})"
  fi
  rm -f "log/$name.pid"
  sleep 2
  holder="$(ss -tlnp 2>/dev/null | grep -E "[:.]${PORT_OF[$name]} " | grep -oP 'pid=\K[0-9]+' | head -1 || true)"
  if [[ -n "${holder:-}" ]] && kill -0 "$holder" 2>/dev/null; then
    kill "$holder" && echo "freed port ${PORT_OF[$name]} (holder pid $holder)" || echo "failed to free port ${PORT_OF[$name]} (holder $holder)"
  fi
done
echo "tailscale mappings kept (they are harmless without backends). Remove with:"
echo "  tailscale serve --https=9445 off; tailscale serve --https=9446 off"
