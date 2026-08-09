#!/bin/bash
# E01 v2 assembly: 23 big slides timed to existing 306s narration + subtitles + VAAPI.
set -euo pipefail
cd /home/vuos/code/p4/e023-build-in-public/ag-01/output
export LIBVA_DRIVER_NAME=radeonsi

AUDIO=narration_mono.mp3
SRT=narration_short.srt
DIR=slides/big

# (slide_idx, start, end) — windows derived from transcript word timestamps
# slide file slide_XX.png
TIMELINE="0 0 5
1 5 18
2 18 33
3 33 44
4 44 57
5 57 63
6 63 77
7 77 90
8 90 99
9 99 111
10 111 122
11 122 131
12 131 139
13 139 147
14 147 155
15 155 168
16 168 181
17 181 198
18 198 219
19 219 243
20 243 252
21 252 270
22 270 306"

# Build per-slide segment files with a slow ken-burns zoom (keep readable, no big motion)
i=0
rm -f slides/big_segments.txt
while read -r idx start end; do
  dur=$(python3 -c "print($end-$start)")
  frames=$(python3 -c "print(int(round($dur*25)))")
  pidx=$(printf "%02d" "$idx")
  seg="$DIR/seg_$i.mp4"
  ffmpeg -v error -y -loop 1 -framerate 25 -i "$DIR/slide_${pidx}.png" \
    -vf "scale=1920:1080,zoompan=z='1+0.0008*on':d=$frames:s=1920x1080:fps=25" \
    -t "$dur" -r 25 -c:v libx264 -pix_fmt yuv420p "$seg" < /dev/null
  echo "seg $i: slide $pidx ${start}s-${end}s (${dur}s)"
  echo "file '$PWD/$seg'" >> slides/big_segments.txt
  i=$((i+1))
done <<< "$TIMELINE"

echo "=== concat segments ==="
ffmpeg -v error -y -f concat -safe 0 -i "$PWD/slides/big_segments.txt" -c copy slides/video_slides.mp4
DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 slides/video_slides.mp4)
echo "slides video duration: ${DUR}s"

echo "=== final: video + audio + subtitles + VAAPI ==="
ffmpeg -v error -y -i slides/video_slides.mp4 -i "$AUDIO" \
  -filter_complex "[0:v]subtitles=${SRT}:force_style='FontSize=30,Alignment=2,MarginV=80,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,Shadow=1'[vsub];[vsub]format=nv12,hwupload[vout]" \
  -map "[vout]" -map 1:a \
  -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -qp 23 \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  episode.mp4

ffprobe -v error -show_streams -select_streams v:0 episode.mp4 2>&1 | rg "encoder|codec_name"
echo "=== done ==="
