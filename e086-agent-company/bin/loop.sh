#!/bin/bash
# Supervisor loop: ticks server so >= min_workers agents stay working.
cd "$(dirname "$0")/.."
PORT=$(python3 -c "import json;d=json.load(open('data/settings.json')) if __import__('os').path.exists('data/settings.json') else json.load(open('needs.json'));print(d['port'])")
tick() { curl -s -X POST "http://127.0.0.1:$PORT/api/loop/tick"; echo; }
case "${1:-one}" in
  one) tick;;
  daemon)
    INT=$(python3 -c "import json,os;print(json.load(open('data/settings.json' if os.path.exists('data/settings.json') else 'needs.json'))['loop_interval_sec'])")
    echo "daemon every ${INT}s (Ctrl-C to stop)"
    while true; do tick; sleep "$INT"; done;;
esac
