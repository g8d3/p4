#!/bin/bash
set -euo pipefail

WORKDIR="/home/vuos/code/p4/e010-more-videos/ag-01"
OUTPUT="$WORKDIR/output"
ENCODED="$OUTPUT/encoded.mp4"
NARRATION="$OUTPUT/narration.mp3"
SUBS="$OUTPUT/subs.srt"
FINAL="$OUTPUT/final.mp4"

export LIBVA_DRIVER_NAME=radeonsi

mkdir -p "$OUTPUT"

echo "=== STEP 1/3: Generating narration ==="
edge-tts --voice es-CO-SalomeNeural \
  --text "Hola, bienvenidos al pipeline de grabación de Wayland. Este es ag-01. Vemos el terminal mostrando neofetch con información del sistema: Ubuntu, AMD Ryzen, GPU Radeon. Luego vemos el directorio del proyecto, el árbol de archivos, uso de memoria y disco. Un cálculo rápido de Python muestra Pi y la raíz cuadrada de dos. Finalmente, la fecha y las interfaces de red. Pipeline completo: Sway headless, grabación wf-recorder, codificación VAAPI." \
  --write-media "$NARRATION" \
  2>/dev/null

NARR_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$NARRATION" 2>/dev/null)
echo "Narration duration: ${NARR_DUR}s"

echo "=== STEP 2/3: Creating subtitles ==="
cat > "$SUBS" << 'SUBTITLES'
1
00:00:00,500 --> 00:00:03,500
Pipeline de grabación Wayland

2
00:00:03,500 --> 00:00:06,500
Sway headless · 608x1080

3
00:00:06,500 --> 00:00:09,000
Neofetch: Ubuntu, AMD Ryzen

4
00:00:09,000 --> 00:00:11,500
Directorio y árbol del proyecto

5
00:00:11,500 --> 00:00:14,000
Memoria y disco

6
00:00:14,000 --> 00:00:16,000
Cálculos con Python

7
00:00:16,000 --> 00:00:19,000
Grabación completada con VAAPI
SUBTITLES

echo "=== STEP 3/3: Combining video + audio + subtitles ==="
VID_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$ENCODED" 2>/dev/null)
echo "Video duration: ${VID_DUR}s"

# Software encoding with subtitles burned in
timeout 60 ffmpeg -y \
  -i "$ENCODED" \
  -i "$NARRATION" \
  -vf "subtitles=${SUBS}:force_style='FontSize=11,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=1,Shadow=1,MarginV=20,Alignment=2'" \
  -c:v libx264 -b:v 2M \
  -c:a aac -b:a 128k \
  -shortest \
  "$FINAL" \
  2>/tmp/ffmpeg-combine.log

echo "=== Final output ==="
ls -lh "$FINAL"
FINAL_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$FINAL" 2>/dev/null)
echo "Final duration: ${FINAL_DUR}s"
echo "Done!"
