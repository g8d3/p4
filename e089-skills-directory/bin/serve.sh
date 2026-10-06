#!/bin/bash
# e089 server. Port/bind from needs.json. No env vars.
set -e
cd "$(dirname "$0")/.."
PORT=$(python3 -c "import json;print(json.load(open('needs.json'))['port'])")
if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then echo "already listening on $PORT"; exit 0; fi
mkdir -p data
nohup python3 server/app.py > server.log 2>&1 &
echo "e089 serving on $PORT (pid $!)"
