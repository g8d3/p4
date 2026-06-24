#!/bin/bash
set -euo pipefail

WORKDIR="/home/vuos/code/p4/e010-more-videos/ag-01"
OUTPUT="$WORKDIR/output"
ENCODED="$OUTPUT/v2_encoded.mp4"
NARRATION="$OUTPUT/v2_narration.mp3"
SUBS="$OUTPUT/v2_subs.srt"
FINAL="$OUTPUT/v2_final.mp4"

export LIBVA_DRIVER_NAME=radeonsi

# Subtitles matching narration text exactly
cat > "$SUBS" << 'SUBTITLES'
1
00:00:00,500 --> 00:00:03,500
Bienvenidos al pipeline de Wayland

2
00:00:04,000 --> 00:00:06,500
Miremos el sistema

3
00:00:07,000 --> 00:00:09,500
Ahora el proyecto

4
00:00:10,000 --> 00:00:12,500
La estructura en árbol

5
00:00:13,000 --> 00:00:15,000
Memoria y disco

6
00:00:15,500 --> 00:00:17,500
Un cálculo con Python

7
00:00:18,000 --> 00:00:19,500
Fecha y red

8
00:00:20,000 --> 00:00:22,500
Pipeline completo
SUBTITLES

echo "Combining..."
timeout 60 ffmpeg -y \
  -i "$ENCODED" \
  -i "$NARRATION" \
  -vf "subtitles=${SUBS}:force_style='FontSize=10,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=15,Alignment=2'" \
  -c:v libx264 -b:v 2M \
  -c:a aac -b:a 128k \
  -shortest \
  "$FINAL" \
  2>/dev/null

ls -lh "$FINAL"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$FINAL" 2>/dev/null
