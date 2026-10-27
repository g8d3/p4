#!/usr/bin/env bash
# Start review server. Port comes from needs.json.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT="$(python3 -c "import json;print(json.load(open('$DIR/needs.json'))['port'])")"
mkdir -p "$DIR/output"
nohup python3 -m http.server "$PORT" --directory "$DIR/site" > "$DIR/output/server.log" 2>&1 &
echo "serving $DIR/site on :$PORT (pid $!)"
