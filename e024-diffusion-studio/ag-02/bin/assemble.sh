#!/usr/bin/env bash
# Assemble the ag-02 tutorial video from slides + narration.
#
# Memory-safe approach: the previous version fed PNGs straight into the concat
# demuxer with an `fps` filter, which ballooned ffmpeg to ~14.6 GB RSS and the
# OOM killer killed it. Instead, each slide is rendered to a short H.264
# segment (loop a still image to its exact duration), segments are concatenated
# with `-c copy`, narration is muxed, then the final encode goes through the
# GPU (h264_vaapi).
#
# Usage: ./assemble.sh
set -euo pipefail
cd "$(dirname "$0")/.."

OUT=output
SEGS="$OUT/segments"
NARRATION="$OUT/narration.mp3"
TIMING="$OUT/timing.json"
mkdir -p "$SEGS"

# 1) Render one segment per slide (looping still, exact per-slide duration).
echo "=== rendering slide segments ==="
python3 - "$TIMING" "$SEGS" <<'EOF'
import json, os, subprocess, sys
timing = json.load(open(sys.argv[1]))
segs = sys.argv[2]
rows = []
for sl in timing["slides"]:
    dur = round(sl["end"] - sl["start"], 3)
    if dur < 0.3:
        continue
    src = f"output/slide-{sl['index']:02d}.png"
    dst = f"{segs}/seg-{sl['index']:02d}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-loop", "1", "-framerate", "25", "-i", src,
           "-t", f"{dur}", "-vf", "format=yuv420p",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", dst]
    subprocess.run(cmd, check=True)
    rows.append(os.path.abspath(dst))
    print(f"  seg-{sl['index']:02d}: {dur}s")
with open("output/segments.list", "w") as f:
    for d in rows:
        f.write(f"file '{d}'\n")
print(f"{len(rows)} segments")
EOF

# 2) Concatenate segments (stream copy, no re-encode, memory-safe).
echo "=== concat segments ==="
timeout 300 ffmpeg -y -loglevel error -f concat -safe 0 -i "$OUT/segments.list" \
  -c copy "$OUT/intermediate.mp4"
ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUT/intermediate.mp4"

# 3) Mux narration (video copy, audio aac) — intermediate.
echo "=== mux narration ==="
timeout 300 ffmpeg -y -loglevel error -i "$OUT/intermediate.mp4" -i "$NARRATION" \
  -c:v copy -c:a aac -b:a 192k -shortest "$OUT/with-audio.mp4"

# 4) Final GPU encode via the p4 wrapper.
echo "=== final GPU encode ==="
../../e023-build-in-public/bin/encode_vaapi.sh "$OUT/with-audio.mp4" "$OUT/first-composition.mp4"

echo "=== done ==="
ls -la "$OUT/first-composition.mp4"
