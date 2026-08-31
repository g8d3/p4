#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
echo "→ Name Studio at http://127.0.0.1:8191"
exec uvicorn app.main:app --host 0.0.0.0 --port 8191 --reload
