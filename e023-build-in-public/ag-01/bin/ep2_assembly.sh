#!/bin/bash
# E02 assembly: static slides -> segments -> concat -> subtitles -> VAAPI final.
set -euo pipefail
cd /home/vuos/code/p4/e023-build-in-public/ag-01/output
export LIBVA_DRIVER_NAME=radeonsi

AUDIO=ep2_narration.mp3
SUBS=ep2_subs.srt
DIR=ep2_slides
TML=ep2_timeline.txt
SEG_DIR=ep2_segments
mkdir -p "$SEG_DIR"

# Build segments (libx264 intermediate — allowed; final is VAAPI)
rm -f "$SEG_DIR/segments.txt"
i=0
while read -r slide start end; do
  [ -z "$slide" ] && continue
  dur=$(python3 -c "print($end-$start)")
  frames=$(python3 -c "print(int(round($dur*25)))")
  [ "$frames" -lt 1 ] && frames=1
  src="$DIR/$slide.png"
  if [ ! -f "$src" ]; then
    echo "MISSING SLIDE: $slide"
    continue
  fi
  seg="$SEG_DIR/seg_$i.mp4"
  ffmpeg -v error -y -loop 1 -framerate 25 -i "$src" \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#0d1117,fps=25" \
    -t "$dur" -r 25 -c:v libx264 -pix_fmt yuv420p "$seg" < /dev/null
  echo "file '$PWD/$seg'" >> "$SEG_DIR/segments.txt"
  echo "seg $i: $slide ${start}s-${end}s"
  i=$((i+1))
done < "$TML"

echo "=== concat ==="
ffmpeg -v error -y -f concat -safe 0 -i "$SEG_DIR/segments.txt" -c copy "$SEG_DIR/video_slides.mp4"
DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$SEG_DIR/video_slides.mp4")
echo "video slides duration: ${DUR}s"

echo "=== final (VAAPI) ==="
ffmpeg -v error -y -i "$SEG_DIR/video_slides.mp4" -i "$AUDIO" \
  -filter_complex "[0:v]subtitles=${PWD}/${SUBS}[vsub];[vsub]format=nv12,hwupload[vout]" \
  -map "[vout]" -map 1:a \
  -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -qp 23 \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  episode.mp4

ffprobe -v error -select_streams v:0 -show_entries stream_tags=encoder -of csv=p=0 episode.mp4
echo "=== done ==="
