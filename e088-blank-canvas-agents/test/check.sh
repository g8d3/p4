#!/bin/bash
# GATE for e088: server health + canvas exists + UI tabs resolve.
set -e
cd "$(dirname "$0")/.."
PORT=$(python3 -c "import json;print(json.load(open('needs.json'))['port'])")
curl -sf "http://127.0.0.1:$PORT/api/health" | grep -q '"ok": true' || { echo "FAIL health"; exit 1; }
curl -sf "http://127.0.0.1:$PORT/api/canvas" | grep -q 'tree' || { echo "FAIL canvas"; exit 1; }
curl -sf "http://127.0.0.1:$PORT/" | grep -q 'tab-canvas' || { echo "FAIL ui"; exit 1; }
curl -sf "http://127.0.0.1:$PORT/" | grep -q 'tab-activity' || { echo "FAIL ui2"; exit 1; }
curl -sf "http://127.0.0.1:$PORT/api/sys" | grep -q '"procs"' || { echo "FAIL sys"; exit 1; }
curl -sf "http://127.0.0.1:$PORT/" | grep -q 'tab-sys' || { echo "FAIL ui3"; exit 1; }
echo "GATE GREEN"
