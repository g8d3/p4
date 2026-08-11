#!/bin/bash
# E01 v4 assembly: ~55 slides (data + charts + IA images + comparisons), static,
# synchronized to narration_fixed.mp3 via transcript_fixed word timestamps. VAAPI.
set -euo pipefail
cd /home/vuos/code/p4/e023-build-in-public/ag-01/output
export LIBVA_DRIVER_NAME=radeonsi

AUDIO=narration_fixed.mp3
SRT=narration_fixed_short.srt
DIR=slides/v3

# timeline: slide  start  end
# Hook + intro
TIMELINE="
d00_title 0 10
img_00 10 15
d01_strategy 15 24
img_01 24 29
d01b_what 29 35
# fake market + synthetic charts
img_02 35 42
d02_synth 42 50
ch_synth_range 50 58
d03_range 58 64
ch_synth_mixed 64 72
d06_mixed 72 80
d04_golive 80 86
# regimes + search
d05_regimes 86 96
d07_search 96 104
img_03 104 110
d08_reb48 110 116
d09_reb96 116 122
d10_oos 122 136
d11_oosseed 136 142
d12_hold 142 150
img_04 150 156
# real data + v1 failure
d13_real 156 168
ch_real_btc_5m 168 176
d14_v1 176 184
t01_v1v2_5m 184 192
d15_fees 192 200
ch_fills_fees 200 208
# v2 redesign + charts
img_05 208 214
d16_v2 214 226
d17_v2_5m 226 238
ch_equity_v1v2_5m 238 250
t02_v1v2_1h 250 256
ch_real_btc_1h 256 262
d18_v2_1h 262 268
# honest truth
img_06 268 274
d19_pf 274 284
d20_ridge 284 292
img_07 292 296
d21_verdict 296 309
d22_thanks 309 315
"

# Build segments: each slide -> static video segment
rm -f slides/v3_segments.txt
i=0
while read -r slide start end; do
  [ -z "$slide" ] && continue
  [ "${slide:0:1}" = "#" ] && continue
  dur=$(python3 -c "print($end-$start)")
  frames=$(python3 -c "print(int(round($dur*25)))")
  [ "$frames" -lt 1 ] && frames=1
  src="$DIR/$slide.png"
  if [ ! -f "$src" ]; then
    echo "MISSING SLIDE: $slide"
    continue
  fi
  seg="$DIR/seg_$i.mp4"
  ffmpeg -v error -y -loop 1 -framerate 25 -i "$src" \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#0d1117,fps=25" \
    -t "$dur" -r 25 -c:v libx264 -pix_fmt yuv420p "$seg" < /dev/null
  echo "file '$PWD/$seg'" >> slides/v3_segments.txt
  echo "seg $i: $slide ${start}s-${end}s"
  i=$((i+1))
done <<< "$TIMELINE"

# concat
echo "=== concat ==="
ffmpeg -v error -y -f concat -safe 0 -i "$PWD/slides/v3_segments.txt" -c copy slides/video_v4.mp4
DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 slides/video_v4.mp4)
echo "video v4 duration: ${DUR}s"

# final
echo "=== final ==="
ffmpeg -v error -y -i slides/video_v4.mp4 -i "$AUDIO" \
  -filter_complex "[0:v]subtitles=${PWD}/${SRT}[vsub];[vsub]format=nv12,hwupload[vout]" \
  -map "[vout]" -map 1:a \
  -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -qp 23 \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  episode_v4.mp4

ffprobe -v error -show_streams -select_streams v:0 episode_v4.mp4 2>&1 | rg "encoder|codec_name"
echo "=== done ==="
