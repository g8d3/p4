#!/usr/bin/env bash
# Assemble the ag-02 tutorial video from slides + narration.
# Reads output/timing.json (slide start/end), builds an intermediate video,
# muxes narration, then final-encodes with h264_vaapi via the p4 wrapper.
#
# Usage: ./assemble.sh
set -euo pipefail
cd "$(dirname "$0")/.."

OUT=output
NARRATION="$OUT/narration.mp3"
TIMING="$OUT/timing.json"

# 1) Build the concat list with per-slide durations from timing.json
python3 - "$TIMING" > /tmp/ag02-concat-video.txt <<'EOF'
import json, sys
timing = json.load(open(sys.argv[1]))
for sl in timing["slides"]:
    dur = round(sl["end"] - sl["start"], 3)
    if dur < 0.2:
        continue
    print(f"file 'output/slide-{sl['index']:02d}.png'")
    print(f"duration {dur}")
# last image needs a second entry to hold its duration in the concat demuxer
last = timing["slides"][-1]
print(f"file 'output/slide-{last['index']:02d}.png'")
EOF

echo "=== concat list ==="
cat /tmp/ag02-concat-video.txt

# 2) Intermediate video-only MP4 (libx264 is allowed for intermediates only)
echo "=== building intermediate ==="
timeout 300 ffmpeg -y -loglevel error -f concat -safe 0 -i /tmp/ag02-concat-video.txt \
  -vf "fps=25,format=yuv420p" -c:v libx264 -preset medium -crf 20 \
  "$OUT/intermediate.mp4"

echo "=== intermediate probe ==="
ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUT/intermediate.mp4"

# 3) Mux narration (video copy, audio aac) — intermediate
echo "=== muxing narration ==="
timeout 300 ffmpeg -y -loglevel error -i "$OUT/intermediate.mp4" -i "$NARRATION" \
  -c:v copy -c:a aac -b:a 192k -shortest "$OUT/with-audio.mp4"

# 4) Final GPU encode via the p4 wrapper
echo "=== final GPU encode ==="
../../e023-build-in-public/bin/encode_vaapi.sh "$OUT/with-audio.mp4" "$OUT/first-composition.mp4"

echo "=== done ==="
ls -la "$OUT/first-composition.mp4"
