#!/bin/bash
set -euo pipefail

WORKDIR="/home/vuos/code/p4/e010-more-videos/ag-01"
OUTPUT="$WORKDIR/output"
SOCK="/tmp/sway-ag02.sock"
RAW="$OUTPUT/v2_raw.mp4"
ENCODED="$OUTPUT/v2_encoded.mp4"
NARRATION="$OUTPUT/v2_narration.mp3"
SUBS="$OUTPUT/v2_subs.srt"
FINAL="$OUTPUT/v2_final.mp4"

export LIBVA_DRIVER_NAME=radeonsi
mkdir -p "$OUTPUT"

cleanup() {
  timeout 3 kill $REC_PID 2>/dev/null || true
  timeout 3 kill $SWAY_PID 2>/dev/null || true
  timeout 3 kill $DEMO_PID 2>/dev/null || true
  rm -f "$SOCK" /tmp/demo_v2.sh
}
trap cleanup EXIT

# --- STEP 1: Generate narration first ---
echo "=== STEP 1: Generating narration ==="
edge-tts --voice es-CO-SalomeNeural \
  --text "Bienvenidos al pipeline de Wayland. Miremos el sistema. Ahora el proyecto. La estructura en árbol. Memoria y disco. Un cálculo con Python. Fecha y red. Pipeline completo." \
  --write-media "$NARRATION" 2>/dev/null

NARR_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$NARRATION")
echo "Narration: ${NARR_DUR}s"

# --- STEP 2: Start Sway ---
echo "=== STEP 2: Starting Sway ==="
rm -f "$SOCK"
SWAYSOCK="$SOCK" WLR_BACKENDS=headless WLR_RENDERER=vulkan WLR_LIBINPUT_NO_DEVICES=1 \
  sway --config "$WORKDIR/sway-headless.conf" 2>/dev/null &
SWAY_PID=$!
sleep 2

# --- STEP 3: Create demo (paced to narration) ---
echo "=== STEP 3: Creating demo ==="
# Total ~22s demo. Narration is ~22s.
cat > /tmp/demo_v2.sh << 'DEMO'
#!/bin/bash
export TERM=xterm-256color
clear
sleep 0.5

echo -e "\033[1;32m"
echo "╔══════════════════════════════════════════════╗"
echo "║  ag-01: Pipeline de Grabación Wayland        ║"
echo "║  Sway headless · 608x1080 · wf-recorder     ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "\033[0m"
sleep 3

echo -e "\033[1;36m── Sistema ──\033[0m"
sleep 0.3
uname -a
sleep 3

echo ""
echo -e "\033[1;36m── Proyecto ──\033[0m"
sleep 0.3
ls -la
sleep 3

echo ""
echo -e "\033[1;36m── Árbol ──\033[0m"
sleep 0.3
tree -L 2 --dirsfirst 2>/dev/null
sleep 3

echo ""
echo -e "\033[1;36m── Memoria ──\033[0m"
sleep 0.3
free -h
sleep 2

echo ""
echo -e "\033[1;36m── Python ──\033[0m"
sleep 0.3
python3 -c "import math; print(f'  Pi={math.pi:.6f}  e={math.e:.6f}')"
sleep 2

echo ""
echo -e "\033[1;36m── Fecha ──\033[0m"
sleep 0.3
date '+%Y-%m-%d %H:%M'
sleep 1.5

echo ""
echo -e "\033[1;36m── Red ──\033[0m"
sleep 0.3
ip -br addr 2>/dev/null | head -2
sleep 1.5

echo ""
echo -e "\033[1;33m"
echo "╔══════════════════════════════════════════════╗"
echo "║  ¡Pipeline completo!                         ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "\033[0m"
sleep 2
DEMO
chmod +x /tmp/demo_v2.sh

# --- STEP 4: Open foot ---
echo "=== STEP 4: Opening foot ==="
WAYLAND_DISPLAY=wayland-1 foot --maximized bash /tmp/demo_v2.sh &
DEMO_PID=$!
sleep 1

# --- STEP 5: Record ---
echo "=== STEP 5: Recording ==="
WAYLAND_DISPLAY=wayland-1 wf-recorder \
  -f "$RAW" --no-dmabuf --no-damage -c libx264 -r 25 \
  2>/dev/null &
REC_PID=$!
sleep 2

# --- STEP 6: Wait ---
echo "=== STEP 6: Waiting for demo ==="
wait $DEMO_PID 2>/dev/null || true
sleep 2

# --- STEP 7: Stop ---
echo "=== STEP 7: Stopping ==="
timeout 5 kill $REC_PID 2>/dev/null || true
wait $REC_PID 2>/dev/null || true
sleep 1

RAW_SIZE=$(stat -c%s "$RAW" 2>/dev/null || echo 0)
VID_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$RAW" 2>/dev/null)
echo "Raw: ${RAW_SIZE} bytes, ${VID_DUR}s"

# --- STEP 8: Encode ---
echo "=== STEP 8: VAAPI encoding ==="
timeout 60 ffmpeg -y -i "$RAW" \
  -vaapi_device /dev/dri/renderD128 \
  -vf "format=nv12,hwupload" \
  -c:v h264_vaapi -b:v 2M -r 25 \
  "$ENCODED" 2>/dev/null || cp "$RAW" "$ENCODED"

ls -lh "$ENCODED"
echo "=== Recording done ==="
