#!/bin/bash
# GPU encode wrapper — THE only way to produce the final video encode.
# Use VAAPI (h264_vaapi) via the AMD GPU. CPU encoders (libx264) are FORBIDDEN
# for final videos; they burn the CPU (loud machine) while the GPU idles.
#
# Usage: encode_vaapi.sh <input> <output>
#   input  - any video ffmpeg can read (capture, concat, or composition)
#   output - .mp4 path; defaults to episode.mp4 if omitted
#
# Rules:
#   - The FINAL video encode MUST go through this script.
#   - wf-recorder capture with -c libx264 is the ONLY allowed libx264 use
#     (fundamentals: VAAPI in wf-recorder corrupts headless captures).
#     That intermediate capture is then re-encoded with this script.
#   - If the input is already h264_vaapi-encoded, this script is a no-op
#     (detected via ffprobe encoder name) and only copies.

set -euo pipefail

IN="${1:?usage: encode_vaapi.sh <input> [output]}"
OUT="${2:-$(dirname "$IN")/episode.mp4}"

export LIBVA_DRIVER_NAME=radeonsi

# Verify input exists
if [ ! -f "$IN" ]; then
  echo "ERROR: input not found: $IN" >&2
  exit 1
fi

# If input was already GPU-encoded, just copy (fast, avoids double loss)
ENCODER=$(ffprobe -v quiet -select_streams v:0 -show_entries stream=codec_name \
  -of csv=p=0 "$IN" 2>/dev/null || echo "")
# VAAPI output stream still reports codec h264; check the encoder tag instead
ENC_TAG=$(ffprobe -v quiet -select_streams v:0 -show_entries stream_tags=encoder \
  -of csv=p=0 "$IN" 2>/dev/null || echo "")
if [[ "$ENC_TAG" == *"vaapi"* ]]; then
  echo "Input already VAAPI-encoded — copying without re-encode"
  cp "$IN" "$OUT"
  exit 0
fi

echo "=== GPU encode (h264_vaapi): $IN -> $OUT ==="
ffmpeg -y -vaapi_device /dev/dri/renderD128 \
  -i "$IN" \
  -vf "format=nv12,hwupload" \
  -c:v h264_vaapi -qp 23 \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  "$OUT" 2>&1 | tail -5

# Verify the result actually used the GPU encoder
ENC_TAG_OUT=$(ffprobe -v quiet -select_streams v:0 -show_entries stream_tags=encoder \
  -of csv=p=0 "$OUT" 2>/dev/null || echo "")
echo "=== encoded with: ${ENC_TAG_OUT:-unknown} ==="
if [[ "$ENC_TAG_OUT" != *"vaapi"* ]]; then
  echo "WARNING: output does not report a VAAPI encoder. Check GPU/VAAPI status." >&2
  exit 2
fi
echo "OK: GPU encode complete -> $OUT"
