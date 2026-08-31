#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"
echo "→ storyo.cc @ http://127.0.0.1:8180/  (branded)"
echo "  /original → faithful infiniteslop.ai mirror"
echo "  /admin    → feedback dashboard"
echo "  proxy → https://infiniteslop.ai for /api/* /live/* /status.json"
node server.js
