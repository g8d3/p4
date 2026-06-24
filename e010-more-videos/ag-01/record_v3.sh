#!/bin/bash
set -euo pipefail

WORKDIR="/home/vuos/code/p4/e010-more-videos/ag-01"
OUTPUT="$WORKDIR/output"
SOCK="/tmp/sway-ag03.sock"
RAW="$OUTPUT/v3_raw.mp4"
ENCODED="$OUTPUT/v3_encoded.mp4"
NARRATION="$OUTPUT/v3_narration.mp3"
SUBS="$OUTPUT/v3_subs.srt"
FINAL="$OUTPUT/v3_final.mp4"

export LIBVA_DRIVER_NAME=radeonsi
mkdir -p "$OUTPUT"

cleanup() {
  timeout 3 kill $REC_PID 2>/dev/null || true
  timeout 3 kill $SWAY_PID 2>/dev/null || true
  timeout 3 kill $DEMO_PID 2>/dev/null || true
  rm -f "$SOCK" /tmp/demo_v3.sh
}
trap cleanup EXIT

# --- STEP 1: Narration first ---
echo "=== STEP 1: Narration ==="
edge-tts --voice es-CO-SalomeNeural \
  --text "Hola, bienvenidos. Soy ag-01 y hoy les muestro cómo grabo pantallas usando Wayland. Primero, miremos qué sistema tenemos. Un AMD Ryzen con Ubuntu. Ahora, veamos los archivos del proyecto. Aquí está el árbol completo. Veamos la memoria: cuatro gigabytes usados. El disco, al ochenta y cuatro por ciento. Ahora un cálculo rápido con Python. Pi y euler. La fecha de hoy. Y las interfaces de red activas. Para terminar, miremos los procesos que consumen más CPU. Y eso es todo. Pipeline completo con Sway, wf-recorder, y VAAPI." \
  --write-media "$NARRATION" 2>/dev/null

NARR_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$NARRATION")
echo "Narration: ${NARR_DUR}s"

# --- STEP 2: Sway ---
echo "=== STEP 2: Sway ==="
rm -f "$SOCK"
SWAYSOCK="$SOCK" WLR_BACKENDS=headless WLR_RENDERER=vulkan WLR_LIBINPUT_NO_DEVICES=1 \
  sway --config "$WORKDIR/sway-headless.conf" 2>/dev/null &
SWAY_PID=$!
sleep 2

# --- STEP 3: Demo script (longer, more sections) ---
echo "=== STEP 3: Demo ==="
cat > /tmp/demo_v3.sh << 'DEMO'
#!/bin/bash
export TERM=xterm-256color
clear
sleep 0.5

echo -e "\033[1;32m"
echo "╔══════════════════════════════════════════════════╗"
echo "║  ag-01: Grabación de Pantalla con Wayland        ║"
echo "║  Sway headless · 608x1080 · wf-recorder · VAAPI ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "\033[0m"
sleep 3

echo -e "\033[1;36m── Sistema ──\033[0m"
sleep 0.3
uname -a
sleep 3.5

echo ""
echo -e "\033[1;36m── Archivos ──\033[0m"
sleep 0.3
ls -la
sleep 3.5

echo ""
echo -e "\033[1;36m── Árbol ──\033[0m"
sleep 0.3
tree -L 2 --dirsfirst 2>/dev/null
sleep 3.5

echo ""
echo -e "\033[1;36m── Memoria ──\033[0m"
sleep 0.3
free -h
sleep 2.5

echo ""
echo -e "\033[1;36m── Disco ──\033[0m"
sleep 0.3
df -h /
sleep 2

echo ""
echo -e "\033[1;36m── Python ──\033[0m"
sleep 0.3
python3 -c "import math; print(f'  Pi={math.pi:.8f}'); print(f'  e={math.e:.8f}'); print(f'  sqrt2={math.sqrt(2):.8f}')"
sleep 2.5

echo ""
echo -e "\033[1;36m── Fecha ──\033[0m"
sleep 0.3
date '+%Y-%m-%d %H:%M:%S'
sleep 1.5

echo ""
echo -e "\033[1;36m── Red ──\033[0m"
sleep 0.3
ip -br addr 2>/dev/null
sleep 2

echo ""
echo -e "\033[1;36m── Top CPU ──\033[0m"
sleep 0.3
ps aux --sort=-%cpu 2>/dev/null | head -5
sleep 2.5

echo ""
echo -e "\033[1;33m"
echo "╔══════════════════════════════════════════════════╗"
echo "║  Pipeline completo. ¡Gracias por ver!            ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "\033[0m"
sleep 2
DEMO
chmod +x /tmp/demo_v3.sh

# --- STEP 4: Foot ---
echo "=== STEP 4: Foot ==="
WAYLAND_DISPLAY=wayland-1 foot --maximized bash /tmp/demo_v3.sh &
DEMO_PID=$!
sleep 1

# --- STEP 5: Record (higher bitrate for 5MB target) ---
echo "=== STEP 5: Record ==="
WAYLAND_DISPLAY=wayland-1 wf-recorder \
  -f "$RAW" --no-dmabuf --no-damage -c libx264 -r 25 \
  -p speed=ultrafast \
  2>/dev/null &
REC_PID=$!
sleep 2

# --- STEP 6: Wait ---
echo "=== STEP 6: Wait ==="
wait $DEMO_PID 2>/dev/null || true
sleep 2

# --- STEP 7: Stop ---
echo "=== STEP 7: Stop ==="
timeout 5 kill $REC_PID 2>/dev/null || true
wait $REC_PID 2>/dev/null || true
sleep 1

RAW_SIZE=$(stat -c%s "$RAW" 2>/dev/null || echo 0)
VID_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$RAW" 2>/dev/null)
echo "Raw: ${RAW_SIZE} bytes, ${VID_DUR}s"

# --- STEP 8: Encode (higher bitrate) ---
echo "=== STEP 8: Encode ==="
timeout 60 ffmpeg -y -i "$RAW" \
  -vaapi_device /dev/dri/renderD128 \
  -vf "format=nv12,hwupload" \
  -c:v h264_vaapi -b:v 4M -r 25 \
  "$ENCODED" 2>/dev/null || cp "$RAW" "$ENCODED"

ls -lh "$ENCODED"
echo "=== Done ==="
