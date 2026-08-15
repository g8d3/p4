#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

for port in 3080 8080 8443; do
  pid=$(ss -tlnp 2>/dev/null | grep ":$port" | grep -oP 'pid=\K[0-9]+' | head -1 || true)
  if [[ -n "${pid:-}" ]]; then
    kill "$pid" 2>/dev/null || true
    echo "stopped $port (pid $pid)"
  fi
done
