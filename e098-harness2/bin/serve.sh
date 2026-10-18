#!/bin/bash
# Serve the rendered results site. Reads port/site from needs.json.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
NEEDS="$HERE/needs.json"
PORT="$(python3 -c "import json;print(json.load(open('$NEEDS'))['port'])")"
SITE="$(python3 -c "import json;print(json.load(open('$NEEDS'))['site_dir'])")"
PIDF="$(python3 -c "import json;print(json.load(open('$NEEDS'))['pid_file'])")"
python3 "$HERE/bin/render.py"
nohup python3 "$HERE/bin/server.py" >/tmp/e098-serve.log 2>&1 &
echo $! > "$PIDF"
sleep 1
curl -s -o /dev/null -w "site HTTP %{http_code}\n" "http://127.0.0.1:$PORT/"
