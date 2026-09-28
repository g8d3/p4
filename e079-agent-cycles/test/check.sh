#!/bin/bash
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=$(python3 -c "import json;print(json.load(open('$DIR/needs.json'))['port'])")
set -e
curl -sf --max-time 10 127.0.0.1:$PORT/api/version | grep -q version
curl -sf --max-time 10 127.0.0.1:$PORT/api/config | grep -q site_name
curl -sf --max-time 10 127.0.0.1:$PORT/api/metrics | grep -q entries
curl -sf --max-time 10 127.0.0.1:$PORT/api/goals | grep -q queued
curl -sf --max-time 10 127.0.0.1:$PORT/api/loop | grep -q install_line
curl -sf --max-time 10 127.0.0.1:$PORT/api/credits | grep -q known
curl -sf --max-time 15 127.0.0.1:$PORT/api/legs/metered | grep -q total_tokens
curl -sf --max-time 10 127.0.0.1:$PORT/ | grep -q "What is happening"
for _p in index.html live.html admin.html; do curl -s --max-time 10 127.0.0.1:$PORT/$_p | python3 -c "import sys,re; h=sys.stdin.read(); ms=re.findall(r\"<script>(.*?)</script>\", h, re.S); open(\"/tmp/_jscheck.js\",\"w\").write(chr(10).join(ms))" && node --check /tmp/_jscheck.js || exit 1; done
curl -sf --max-time 10 127.0.0.1:$PORT/ | grep -q "Share it"
curl -sf --max-time 10 127.0.0.1:$PORT/admin.html | grep -q "Referrals"
curl -sf --max-time 10 127.0.0.1:$PORT/live.html | grep -q "Live leg"
curl -s --max-time 10 127.0.0.1:$PORT/api/leg?cycle=c026 | grep -q verdict
curl -sf --max-time 10 127.0.0.1:$PORT/ | grep -q 'id="why"'
curl -sf --max-time 10 127.0.0.1:$PORT/ | grep -q "legs/'"
curl -sf --max-time 10 127.0.0.1:$PORT/admin.html | grep -q "gwhy"
curl -sf --max-time 10 -X POST 127.0.0.1:$PORT/api/ref -H 'Content-Type: application/json' -d '{"code":"selftest"}' | grep -q ok
curl -sf --max-time 10 127.0.0.1:$PORT/api/refs | grep -q selftest
echo PASS
