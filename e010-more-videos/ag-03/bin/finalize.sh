#!/bin/bash
# Combine: trimmed video + narration/TTS audio + TikTok-style subtitles
set -e

BASE="/home/vuos/code/p4/e010-more-videos/ag-03"
VIDEO_IN="$BASE/output/recording_raw.mp4"
AUDIO_IN="$BASE/assets/audio_final.wav"
SRT="$BASE/assets/subtitles.srt"
OUT="$BASE/output/demo.mp4"
TRIM=2  # seconds to trim from start

echo "=== Combining video + audio + subtitles ==="
echo "Video: $VIDEO_IN"
echo "Audio: $AUDIO_IN"
echo "Subtitles: $SRT"

# Trim first 2s, burn subtitles (TikTok style), add audio
# Subtitles: bottom center, white bold text, black outline
timeout 120 ffmpeg -y \
    -ss "$TRIM" \
    -i "$VIDEO_IN" \
    -i "$AUDIO_IN" \
    -vf "subtitles='$SRT':force_style='Bold=1,FontSize=26,Outline=3,Shadow=1,Alignment=2,MarginV=10'" \
    -map 0:v:0 -map 1:a:0 \
    -c:v libx264 -preset fast -crf 20 \
    -b:v 2M \
    -c:a aac -b:a 128k \
    -shortest \
    -pix_fmt yuv420p \
    "$OUT" 2>&1

echo ""
echo "=== Final output ==="
ls -lh "$OUT"
ffprobe -v error -show_entries format=duration,size,bit_rate \
    -show_entries stream=codec_name,codec_type,width,height,r_frame_rate,channels \
    -of json "$OUT" 2>&1
