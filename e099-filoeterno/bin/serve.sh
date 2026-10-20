#!/bin/bash
# Serve the glass wall + loop actions. Reads port/site from needs.json.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
NEEDS="$HERE/needs.json"
PORT="$(python3 -c "import json;print(json.load(open('$NEEDS'))['port'])")"
PIDF="$(python3 -c "import json;print(json.load(open('$NEEDS'))['pid_file'])")"
python3 "$HERE/bin/render.py"
nohup python3 "$HERE/bin/server.py" >/tmp/e099-serve.log 2>&1 &
echo $! > "$PIDF"
sleep 1
curl -s -o /dev/null -w "glass wall HTTP %{http_code}\n" "http://127.0.0.1:$PORT/"
