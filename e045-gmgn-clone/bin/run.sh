#!/usr/bin/env bash
# Run the GMGN clone. Binds 0.0.0.0 so it works from the phone on LAN.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${GMGN_PORT:-8338}"
echo "GMGN clone → http://0.0.0.0:${PORT}" >&2
exec python3 app.py
