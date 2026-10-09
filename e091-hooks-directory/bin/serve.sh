#!/bin/bash
# e091 server. Port/bind from needs.json. No env vars.
set -e
cd "$(dirname "$0")/.."
PORT=$(python3 -c "import json;print(json.load(open('needs.json'))['port'])")
if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then echo "already listening on $PORT"; exit 0; fi
nohup python3 server/app.py > server.log 2>&1 &
echo "e091 serving on $PORT (pid $!)"
