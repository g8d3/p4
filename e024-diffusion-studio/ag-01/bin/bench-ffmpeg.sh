#!/bin/bash
# Benchmark: ffmpeg h264_vaapi equivalent of the p4-media composition.
export LIBVA_DRIVER_NAME=radeonsi
set -euo pipefail
cd "$(dirname "$0")/../output"

START=$(date +%s.%N)
ffmpeg -y -vaapi_device /dev/dri/renderD128 \
  -ss 40 -t 14 -i /home/vuos/code/p4/e023-build-in-public/ag-02/output/episode.mp4 \
  -i /home/vuos/code/p4/e024-diffusion-studio/ag-01/output/narration-p4media.mp3 \
  -filter_complex "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,drawbox=x=0:y=0:w=1920:h=1080:color=black@0.5:t=fill,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='Real p4 footage, imported':fontcolor=white:fontsize=90:x=(w-text_w)/2:y=80,format=nv12,hwupload[v]" \
  -map "[v]" -map 1:a \
  -c:v h264_vaapi -qp 23 -c:a aac -b:a 192k \
  -movflags +faststart \
  benchmark-ffmpeg.mp4 \
  > /tmp/opencode/bench-ffmpeg.log 2>&1
END=$(date +%s.%N)
echo "ffmpeg wall: $(echo "$END - $START" | bc)s"
tail -3 /tmp/opencode/bench-ffmpeg.log
ffprobe -v quiet -select_streams v:0 -show_entries stream_tags=encoder -of csv=p=0 benchmark-ffmpeg.mp4
ls -la benchmark-ffmpeg.mp4
