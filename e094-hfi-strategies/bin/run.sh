#!/bin/bash
# e094: start server on needs.json port
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=$(python3 -c "import json;print(json.load(open('$DIR/needs.json'))['port'])")
exec python3 "$DIR/server/app.py"
