#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -q -r requirements.txt
else
  source .venv/bin/activate
fi
exec python -m cli.cli "$@"
