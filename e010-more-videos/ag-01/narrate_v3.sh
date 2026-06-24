#!/bin/bash
set -euo pipefail

WORKDIR="/home/vuos/code/p4/e010-more-videos/ag-01"
OUTPUT="$WORKDIR/output"
ENCODED="$OUTPUT/v3_encoded.mp4"
NARRATION="$OUTPUT/v3_narration.mp3"
SUBS="$OUTPUT/v3_subs.srt"
FINAL="$OUTPUT/v3_final.mp4"

export LIBVA_DRIVER_NAME=radeonsi

cat > "$SUBS" << 'SUBTITLES'
1
00:00:00,500 --> 00:00:03,500
Hola, bienvenidos. Soy ag-01
y hoy les muestro cómo grabo pantallas

2
00:00:04,000 --> 00:00:06,500
usando Wayland. Primero,
miremos qué sistema tenemos

3
00:00:07,000 --> 00:00:09,500
Un AMD Ryzen con Ubuntu

4
00:00:10,000 --> 00:00:12,500
Ahora, veamos los archivos
del proyecto

5
00:00:13,000 --> 00:00:15,500
Aquí está el árbol completo

6
00:00:16,000 --> 00:00:18,000
Veamos la memoria:
cuatro gigabytes usados

7
00:00:18,500 --> 00:00:20,500
El disco, al ochenta
y cuatro por ciento

8
00:00:21,000 --> 00:00:23,500
Ahora un cálculo rápido
con Python. Pi y euler

9
00:00:24,000 --> 00:00:25,500
La fecha de hoy

10
00:00:26,000 --> 00:00:28,000
Y las interfaces de red activas

11
00:00:28,500 --> 00:00:31,000
Para terminar, miremos los procesos
que consumen más CPU

12
00:00:31,500 --> 00:00:34,500
Y eso es todo. Pipeline completo
con Sway, wf-recorder, y VAAPI
SUBTITLES

echo "Combining..."
timeout 60 ffmpeg -y \
  -i "$ENCODED" \
  -i "$NARRATION" \
  -vf "subtitles=${SUBS}:force_style='FontSize=10,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=4,Outline=0,Shadow=0,MarginV=15,Alignment=2'" \
  -c:v libx264 -b:v 4M \
  -c:a aac -b:a 128k \
  -shortest \
  "$FINAL" \
  2>/dev/null

ls -lh "$FINAL"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$FINAL" 2>/dev/null
