#!/bin/bash
# Build base segments fresh (1920x1080), verify each, then assemble v3.
set -euo pipefail
cd /home/vuos/code/p4/e023-build-in-public/ag-01/output

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

while read -r idx start end; do
  dur=$(python3 -c "print($end-$start)")
  frames=$(python3 -c "print(int(round($dur*25)))")
  pidx=$(printf "%02d" "$idx")
  ffmpeg -v error -y -loop 1 -framerate 25 -i "slides/big/slide_${pidx}.png" \
    -vf "scale=1920:1080,zoompan=z='1+0.0008*on':d=$frames:s=1920x1080:fps=25" \
    -t "$dur" -r 25 -c:v libx264 -pix_fmt yuv420p "slides/big/seg_${pidx}.mp4" < /dev/null
  dims=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "slides/big/seg_${pidx}.mp4")
  echo "seg ${pidx}: ${dims} (${dur}s)"
done <<< "$TIMELINE"
echo "=== all base segments built ==="
