#!/bin/bash
# E01 v2 assembly (robust): burn subtitles per-segment (shifted times), then concat, then VAAPI.
set -euo pipefail
cd /home/vuos/code/p4/e023-build-in-public/ag-01/output
export LIBVA_DRIVER_NAME=radeonsi

AUDIO=narration_mono.mp3
DIR=slides/big
STYLE="FontSize=48,Alignment=2,MarginV=80,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=3,Shadow=1"

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

# Generate per-segment shifted SRTs + ASS files (ass filter works; subtitles/srt fails on PNG-derived input)
export TL="$TIMELINE"
python3 - << 'PYEOF'
import re, os
cues=[]
for b in open('narration_short.srt').read().strip().split('\n\n'):
    l=b.split('\n')
    m=re.match(r'(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)',l[1])
    if m:
        t0=int(m.group(1))*3600+int(m.group(2))*60+int(m.group(3))+int(m.group(4))/1000
        t1=int(m.group(5))*3600+int(m.group(6))*60+int(m.group(7))+int(m.group(8))/1000
        cues.append((t0,t1,' '.join(l[2:])))
def ts(x):
    h=int(x//3600);m=int((x%3600)//60);s=x%60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s-int(s))*1000)):03d}'
def ass_ts(x):
    h=int(x//3600);m=int((x%3600)//60);s=x%60
    return f'{h}:{m}:{s:05.2f}'
ASS_HEADER='''[Script Info]
PlayResX: 1920
PlayResY: 1080
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub, Arial, 48, &H00FFFFFF, &H00FFFFFF, &H00000000, &H00000000, 0, 0, 0, 0, 100, 100, 0, 0, 1, 3, 1, 2, 60, 60, 80, 1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
os.makedirs('slides/seg_srt', exist_ok=True)
segs=[]
for line in os.environ['TL'].strip().split('\n'):
    idx,start,end=line.split()
    segs.append((int(idx),int(start),int(end)))
for idx,start,end in segs:
    seg_cues=[c for c in cues if c[1]>start and c[0]<end]
    with open(f'slides/seg_srt/seg_{idx:02d}.srt','w') as f:
        for j,(a,b,txt) in enumerate(seg_cues,1):
            sa=max(0.0, a-start)
            sb=max(0.0, b-start)
            if sb<=sa:
                sb=sa+0.1
            f.write(f'{j}\n{ts(sa)} --> {ts(sb)}\n{txt}\n\n')
    with open(f'slides/seg_srt/seg_{idx:02d}.ass','w') as f:
        f.write(ASS_HEADER)
        for a,b,txt in seg_cues:
            sa=max(0.0, a-start)
            sb=max(0.0, b-start)
            if sb<=sa:
                sb=sa+0.1
            clean=txt.replace('{','[').replace('}',']')
            f.write(f'Dialogue: 0,{ass_ts(sa)},{ass_ts(sb)},Sub,,0,0,0,,{clean}\n')
    print(f'seg {idx:02d}: {len(seg_cues)} cues ({start}-{end})')
PYEOF

# Burn subtitles per segment (ass filter) + concat
rm -f slides/seg_subs.txt
i=0
while read -r idx start end; do
  pidx=$(printf "%02d" "$idx")
  ass="slides/seg_srt/seg_${pidx}.ass"
  out="slides/big/subbed_${pidx}.mp4"
  if [ ! -s "$ass" ]; then
    cp "slides/big/seg_${pidx}.mp4" "$out"
  else
    ffmpeg -v error -y -i "slides/big/seg_${pidx}.mp4" \
      -vf "ass=${PWD}/${ass}" \
      -c:v libx264 -pix_fmt yuv420p -r 25 "$out" < /dev/null
  fi
  echo "file '$PWD/$out'" >> slides/seg_subs.txt
  echo "subbed seg $pidx"
  i=$((i+1))
done <<< "$TIMELINE"

echo "=== concat subbed segments ==="
ffmpeg -v error -y -f concat -safe 0 -i "$PWD/slides/seg_subs.txt" -c copy slides/video_slides_subbed.mp4
DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 slides/video_slides_subbed.mp4)
echo "subbed slides duration: ${DUR}s"

echo "=== final: video + audio + VAAPI ==="
ffmpeg -v error -y -i slides/video_slides_subbed.mp4 -i "$AUDIO" \
  -map 0:v -map 1:a \
  -vaapi_device /dev/dri/renderD128 \
  -vf "format=nv12,hwupload" \
  -c:v h264_vaapi -qp 23 \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  episode.mp4

ffprobe -v error -show_streams -select_streams v:0 episode.mp4 2>&1 | rg "encoder|codec_name"
echo "=== done ==="
