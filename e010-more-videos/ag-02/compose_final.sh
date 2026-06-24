#!/bin/bash
# compose_final.sh — Compose final video: screen recording + narration + subtitles

set -euo pipefail

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="$WORKDIR/output"

SCREEN_RAW="$OUTPUT/screen_raw.mp4"
NARRATION="$OUTPUT/narration.mp3"
SUBS="$OUTPUT/subs/narration.srt"
FINAL="$OUTPUT/final.mp4"

echo "=== Composing final video ==="

# Check inputs
for f in "$SCREEN_RAW" "$NARRATION" "$SUBS"; do
    if [ ! -f "$f" ]; then
        echo "ERROR: Missing $f"
        exit 1
    fi
done

# Get durations
SCREEN_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$SCREEN_RAW" 2>/dev/null || echo "60")
AUDIO_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$NARRATION" 2>/dev/null || echo "30")

echo "Screen duration: ${SCREEN_DUR}s"
echo "Audio duration: ${AUDIO_DUR}s"

# Strategy: trim screen recording to match audio, overlay subtitles, mix audio
# Use the shorter of screen/audio duration
COMP_DUR=$(python3 -c "print(min(float('$SCREEN_DUR'), float('$AUDIO_DUR'), 120))")

echo "Composing ${COMP_DUR}s video..."

# Build ffmpeg filter complex:
# 1. Trim screen recording
# 2. Overlay subtitles (SRT with TikTok style)
# 3. Mix original audio (if any) with narration
export LIBVA_DRIVER_NAME=radeonsi

timeout 120 ffmpeg -y \
    -i "$SCREEN_RAW" \
    -i "$NARRATION" \
    -filter_complex "
        [0:v]trim=0:${COMP_DUR},setpts=PTS-STARTPTS,fps=15,scale=608:1080[bg];
        [bg]subtitles='${SUBS}':force_style='FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,Alignment=2,MarginV=60'[vout];
        [1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[aout]
    " \
    -map "[vout]" -map "[aout]" \
    -c:v libx264 -pix_fmt yuv420p -preset fast -crf 23 \
    -c:a aac -b:a 128k \
    -t "$COMP_DUR" \
    -movflags +faststart \
    "$FINAL" 2>/dev/null || \
timeout 120 ffmpeg -y \
    -i "$SCREEN_RAW" \
    -i "$NARRATION" \
    -filter_complex "
        [0:v]trim=0:${COMP_DUR},setpts=PTS-STARTPTS,fps=15,scale=608:1080[bg];
        [bg]subtitles='${SUBS}':force_style='FontSize=18,PrimaryColour=&H00FFFFFF,Outline=2,Alignment=2,MarginV=60'[vout];
        [1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[aout]
    " \
    -map "[vout]" -map "[aout]" \
    -c:v libx264 -pix_fmt yuv420p -preset fast -crf 23 \
    -c:a aac -b:a 128k \
    -t "$COMP_DUR" \
    -movflags +faststart \
    "$FINAL" 2>/dev/null

# Verify
if [ -f "$FINAL" ]; then
    SIZE=$(stat -c%s "$FINAL" 2>/dev/null || stat -f%z "$FINAL" 2>/dev/null || echo "0")
    DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$FINAL" 2>/dev/null || echo "0")
    echo "Final video: $FINAL"
    echo "Size: $(( SIZE / 1024 )) KB"
    echo "Duration: ${DURATION}s"
else
    echo "ERROR: Final video not created"
    exit 1
fi
