#!/bin/bash
# E03 (Pro control) assembly: slides + monitor clip -> segments -> concat -> subtitles -> VAAPI.
set -euo pipefail
cd /home/vuos/code/p4/e023-build-in-public/ag-04-pro-control/output
export LIBVA_DRIVER_NAME=radeonsi

AUDIO=narration.mp3
SUBS=subs.srt
DIR=slides
TML=timeline.txt
SEG_DIR=segments
MON=../output/capture/mon_capture_raw.mp4
mkdir -p "$SEG_DIR"

# Build segments (libx264 intermediate — allowed; final is VAAPI)
rm -f "$SEG_DIR/segments.txt"
i=0
while read -r slide start end; do
  [ -z "$slide" ] && continue
  dur=$(python3 -c "print(round($end-$start,3))")
  seg="$SEG_DIR/seg_$i.mp4"
  if [ "$slide" = "mon_capture" ]; then
    # real captured terminal: cut the monitor clip to the exact window
    ffmpeg -v error -y -i "$MON" -t "$dur" -r 25 -c:v libx264 -pix_fmt yuv420p -preset veryfast "$seg" < /dev/null
  else
    src="$DIR/$slide.png"
    if [ ! -f "$src" ]; then
      echo "MISSING SLIDE: $slide" >&2
      continue
    fi
    ffmpeg -v error -y -loop 1 -framerate 25 -i "$src" \
      -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#0d1117,fps=25" \
      -t "$dur" -r 25 -c:v libx264 -pix_fmt yuv420p -preset veryfast "$seg" < /dev/null
  fi
  echo "file '$PWD/$seg'" >> "$SEG_DIR/segments.txt"
  echo "seg $i: $slide ${start}s-${end}s (${dur}s)"
  i=$((i+1))
done < "$TML"

echo "=== concat ==="
ffmpeg -v error -y -f concat -safe 0 -i "$SEG_DIR/segments.txt" -c copy "$SEG_DIR/video_slides.mp4"
DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$SEG_DIR/video_slides.mp4")
echo "video slides duration: ${DUR}s"

echo "=== final (VAAPI + subtitles) ==="
ffmpeg -v error -y -i "$SEG_DIR/video_slides.mp4" -i "$AUDIO" \
  -filter_complex "[0:v]subtitles=${PWD}/${SUBS}[vsub];[vsub]format=nv12,hwupload[vout]" \
  -map "[vout]" -map 1:a \
  -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -qp 23 \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  -t "$DUR" \
  episode.mp4

ffprobe -v error -select_streams v:0 -show_entries stream_tags=encoder -of csv=p=0 episode.mp4
echo "=== done ==="
