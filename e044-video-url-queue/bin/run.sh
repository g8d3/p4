#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi

HOST="${URLQ_HOST:-0.0.0.0}"
PORT="${URLQ_PORT:-8177}"
exec ./.venv/bin/uvicorn app.main:app --host "$HOST" --port "$PORT" "$@"
