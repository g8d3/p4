#!/usr/bin/env bash
# Full pipeline: detect setup -> build composition -> check -> render -> vaapi encode.
# Usage: bin/run_pipeline.sh [--force]   (--force = drill on nearest real level)
set -euo pipefail
EXP="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$EXP"

echo "=== 1/4 detect ==="
timeout 120 python3 ag-01-setup/bin/detect_setup.py "$@"

if [ ! -f ag-01-setup/output/setup.json ]; then
  echo "No setup fired (no_setup.json written). Nothing to render."
  exit 0
fi

echo "=== 2/4 build composition ==="
timeout 60 python3 ag-02-video/bin/build_composition.py

echo "=== 3/4 check ==="
cd ag-02-video/alert-short
timeout 300 npm run check

echo "=== 4/4 render + encode ==="
timeout 900 npx hyperframes render -o renders/alert-raw.mp4
timeout 300 /home/vuos/code/p4/e023-build-in-public/bin/encode_vaapi.sh \
  renders/alert-raw.mp4 renders/alert.mp4
ENC="$(ffprobe -v quiet -select_streams v:0 -show_entries stream_tags=encoder -of csv=p=0 renders/alert.mp4)"
case "$ENC" in
  *vaapi*) echo "OK: renders/alert.mp4 ($ENC)" ;;
  *) echo "FAIL: encoder tag is not vaapi: $ENC"; exit 1 ;;
esac
