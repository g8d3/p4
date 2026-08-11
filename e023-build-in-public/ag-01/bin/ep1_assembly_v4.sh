#!/bin/bash
# E01 v3 assembly: 40 static slides synchronized to narration_fixed.mp3, no Ken Burns.
# Subtitles from narration_fixed_short.srt (new transcript). VAAPI encode.
set -euo pipefail
cd /home/vuos/code/p4/e023-build-in-public/ag-01/output
export LIBVA_DRIVER_NAME=radeonsi

AUDIO=narration_fixed.mp3
SRT=narration_fixed_short.srt
DIR=slides/v3

# timeline: slide_file  start  end   (times from transcript_fixed word timestamps)
TIMELINE="
d00_title 0 10
d01_strategy 10 34
img_00 34 44
d02_synth 44 58
d03_range 58 66
d04_golive 66 74
d05_regimes 74 86
d06_mixed 86 100
img_01 100 110
d07_search 110 115
d08_reb48 115 121
d09_reb96 121 125
d10_oos 125 140
d11_oosseed 140 144
d12_hold 144 155
img_02 155 160
d13_real 160 172
d14_v1 172 180
t01_v1v2_5m 180 190
d15_fees 190 204
img_03 204 210
d16_v2 210 237
d17_v2_5m 237 250
t02_v1v2_1h 250 256
d18_v2_1h 256 260
d19_pf 260 272
d20_ridge 272 283
img_04 283 292
d21_verdict 292 309
d22_thanks 309 315
eq_v1_5m 315 316
"

# Build segments: each slide -> static video segment of (end-start), 25fps
rm -f slides/v3_segments.txt
i=0
while read -r slide start end; do
  [ -z "$slide" ] && continue
  dur=$(python3 -c "print($end-$start)")
  frames=$(python3 -c "print(int(round($dur*25)))")
  if [ "$frames" -lt 1 ]; then frames=1; fi
  seg="$DIR/seg_$i.mp4"
  ffmpeg -v error -y -loop 1 -framerate 25 -i "$DIR/$slide.png" \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#0d1117,fps=25" \
    -t "$dur" -r 25 -c:v libx264 -pix_fmt yuv420p "$seg" < /dev/null
  echo "file '$PWD/$seg'" >> slides/v3_segments.txt
  echo "seg $i: $slide ${start}s-${end}s"
  i=$((i+1))
done <<< "$TIMELINE"

# concat
echo "=== concat ==="
ffmpeg -v error -y -f concat -safe 0 -i "$PWD/slides/v3_segments.txt" -c copy slides/video_v3.mp4
DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 slides/video_v3.mp4)
echo "video v3 duration: ${DUR}s"

# final: video + audio + subtitles + VAAPI
echo "=== final ==="
ffmpeg -v error -y -i slides/video_v3.mp4 -i "$AUDIO" \
  -filter_complex "[0:v]subtitles=${PWD}/${SRT}[vsub];[vsub]format=nv12,hwupload[vout]" \
  -map "[vout]" -map 1:a \
  -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -qp 23 \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  episode_v3.mp4

ffprobe -v error -show_streams -select_streams v:0 episode_v3.mp4 2>&1 | rg "encoder|codec_name"
echo "=== done ==="
