#!/usr/bin/env bash
# Start the Hyperliquid Playground server (mobile-first web UI).
# Access from your phone: http://<this-machine-ip>:8310
set -euo pipefail
cd "$(dirname "$0")"
exec uvicorn hl_playground.app:app --host 0.0.0.0 --port "${HL_PORT:-8310}"
