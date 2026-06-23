#!/bin/bash
set -e

DIR="/home/vuos/code/p4/e010-more-videos/ag-03"
FRAMES="$DIR/assets/frames"
AUDIO="$DIR/assets/audio_mix.aac"
OUT="$DIR/output/demo.mp4"

mkdir -p "$DIR/output"

echo "=== Encoding video from frames + audio ==="
echo "Frames: $(ls "$FRAMES"/frame_*.png | wc -l)"
echo "Audio: $AUDIO"

# Try VAAPI hardware encoding, fall back to software
timeout 120 ffmpeg -y \
  -framerate 15 \
  -i "$FRAMES/frame_%05d.png" \
  -i "$AUDIO" \
  -c:v h264_vaapi \
  -vaapi_device /dev/dri/renderD128 \
  -vf "format=nv12,hwupload,scale=608:1080" \
  -b:v 2M \
  -c:a aac -b:a 128k \
  -shortest \
  -pix_fmt yuv420p \
  "$OUT" 2>&1 || {
    echo "VAAPI failed, falling back to libx264..."
        timeout 180 ffmpeg -y \
      -framerate 15 \
      -i "$FRAMES/frame_%05d.png" \
      -i "$AUDIO" \
      -c:v libx264 -preset fast -crf 23 \
      -b:v 2M \
      -c:a aac -b:a 128k \
      -shortest \
      -pix_fmt yuv420p \
      "$OUT" 2>&1
  }

echo ""
echo "=== Output ==="
ls -la "$OUT"
ffprobe -v error -show_entries format=duration,size,bit_rate \
  -show_entries stream=codec_name,width,height,r_frame_rate \
  -of json "$OUT" 2>&1
