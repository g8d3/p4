#!/bin/bash
# Definitive assembly: bake subtitles per-segment, concat, VAAPI encode.
set -e
cd /home/vuos/code/p4/e023-build-in-public/ag-01/output
export LIBVA_DRIVER_NAME=radeonsi

python3 - << 'PYEOF'
# shift SRT times by +190s for the verdict segment
import re
def shift(fn, out, offset):
    outl=[]
    for line in open(fn).read().splitlines():
        m=re.match(r'(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)', line)
        if m:
            def t(g):
                return int(g(1))*3600+int(g(2))*60+int(g(3))+int(g(4))/1000
            a=t(m.group)+offset; b=t(m.group)+offset
            def ts(x):
                h=int(x//3600);m=int((x%3600)//60);s=x%60
                return f'{h:02d}:{m:02d}:{int(s):02d},{int((s-int(s))*1000):03d}'
            line=f'{ts(a)} --> {ts(b)}'
        outl.append(line)
    open(out,'w').write('\n'.join(outl)+'\n')
shift('narration_short.srt','narration_shift.srt',190)
print('wrote narration_shift.srt')
PYEOF

STYLE="FontSize=26,Alignment=2,MarginV=70,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,Shadow=1"

echo "== bake subs segment 1 =="
ffmpeg -v error -y -i capture/segment_capture.mp4 \
  -vf "subtitles=narration_short.srt:force_style='$STYLE'" \
  -c:v libx264 -pix_fmt yuv420p -r 25 seg1_subbed.mp4

echo "== bake subs segment 2 =="
ffmpeg -v error -y -i slides/verdict_segment.mp4 \
  -vf "subtitles=narration_shift.srt:force_style='$STYLE'" \
  -c:v libx264 -pix_fmt yuv420p -r 25 seg2_subbed.mp4

echo "== concat + narration audio + VAAPI =="
printf "file 'seg1_subbed.mp4'\nfile 'seg2_subbed.mp4'\n" > concat2.txt
ffmpeg -v error -y -f concat -safe 0 -i concat2.txt -i narration_mono.mp3 \
  -map 0:v -map 1:a \
  -vaapi_device /dev/dri/renderD128 \
  -vf "format=nv12,hwupload" \
  -c:v h264_vaapi -qp 23 \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  episode.mp4

ffprobe -v error -show_streams -select_streams v:0 episode.mp4 2>&1 | rg "encoder|codec_name"
echo "done"
