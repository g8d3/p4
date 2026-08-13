#!/usr/bin/env bash
# Concatenate the KIE Gemini TTS parts into a single narration file, preserving
# the native sample rate (24 kHz). The KIE TTS helper truncates long requests
# (~106 s max), so the script narration is TTS'd in parts named
# `kie-tts_part<N>_<ts>.mp3`. This script joins them in part order.
#
# Usage: ./make_narration.sh  [output.mp3]   (default: output/narration.mp3)
#
# Pitfall this avoids: an earlier manual concat resampled 24 kHz -> 16 kHz.
# `-c copy` keeps the original streams untouched.
set -euo pipefail
cd "$(dirname "$0")/.."

OUT="${1:-output/narration.mp3}"

# collect parts, sorted by the part number in the filename
mapfile -t PARTS < <(ls output/kie-tts_part*.mp3 2>/dev/null \
  | sort -t p -k3 -n || true)
if [ "${#PARTS[@]}" -eq 0 ]; then
  echo "ERROR: no KIE TTS parts found (output/kie-tts_part*.mp3)" >&2
  exit 1
fi

LIST="output/parts.list"
: > "$LIST"
for p in "${PARTS[@]}"; do
  printf "file '%s'\n" "$(realpath "$p")" >> "$LIST"
done
echo "concatenating ${#PARTS[@]} parts:"
cat "$LIST"

timeout 120 ffmpeg -y -loglevel error -f concat -safe 0 -i "$LIST" -c copy "$OUT"

echo "=== result ==="
ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT"
ffprobe -v error -show_entries stream=codec_name,sample_rate,channels -of csv=p=0 "$OUT"
