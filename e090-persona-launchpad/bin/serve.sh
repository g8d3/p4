#!/bin/bash
cd "$(dirname "$0")/.."
PORT=$(python3 -c "import json;print(json.load(open('needs.json'))['port'])")
python3 server/app.py
