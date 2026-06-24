#!/bin/bash
set -euo pipefail

WORKDIR="/home/vuos/code/p4/e010-more-videos/ag-01"
OUTPUT="$WORKDIR/output"
SOCK="/tmp/sway-ag01.sock"
SWAY_LOG="/tmp/sway-ag01.log"
WF_LOG="/tmp/wf-recorder-ag01.log"
RAW="$OUTPUT/raw_capture.mp4"
ENCODED="$OUTPUT/encoded.mp4"
NARRATION="$OUTPUT/narration.mp3"
SUBS="$OUTPUT/subs.srt"
FINAL="$OUTPUT/final.mp4"
DEMO_SCRIPT="/tmp/demo_ag01.sh"

export LIBVA_DRIVER_NAME=radeonsi

mkdir -p "$OUTPUT"
rm -f "$RAW" "$ENCODED" "$NARRATION" "$SUBS" "$FINAL"

cleanup() {
  echo "Cleaning up..."
  timeout 3 kill $REC_PID 2>/dev/null || true
  timeout 3 kill $SWAY_PID 2>/dev/null || true
  timeout 3 kill $DEMO_PID 2>/dev/null || true
  rm -f "$SOCK" "$DEMO_SCRIPT"
}
trap cleanup EXIT

echo "=== STEP 1/7: Starting Sway headless (608x1080) ==="
rm -f "$SOCK"
SWAYSOCK="$SOCK" WLR_BACKENDS=headless WLR_RENDERER=vulkan WLR_LIBINPUT_NO_DEVICES=1 \
  sway --config "$WORKDIR/sway-headless.conf" 2>"$SWAY_LOG" &
SWAY_PID=$!
sleep 2

if ! kill -0 "$SWAY_PID" 2>/dev/null; then
  echo "FATAL: Sway failed to start"
  cat "$SWAY_LOG"
  exit 1
fi
echo "Sway running (PID=$SWAY_PID)"

echo "=== STEP 2/7: Creating demo script ==="
cat > "$DEMO_SCRIPT" << 'SCRIPT'
#!/bin/bash
export TERM=xterm-256color

clear
sleep 0.3

echo -e "\033[1;32m"
echo "╔═══════════════════════════════════════════════════╗"
echo "║      ag-01: Wayland Virtual Display Pipeline     ║"
echo "║      Sway Headless · 608x1080 · wf-recorder     ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "\033[0m"
sleep 1.5

echo -e "\033[1;36m── System ──\033[0m"
sleep 0.3
uname -a
sleep 1

echo ""
echo -e "\033[1;36m── Neofetch ──\033[0m"
sleep 0.3
neofetch --off 2>/dev/null || echo "(neofetch display not available in headless)"
sleep 2

echo ""
echo -e "\033[1;36m── Directory ──\033[0m"
sleep 0.3
pwd && ls -la
sleep 1.5

echo ""
echo -e "\033[1;36m── Project Tree ──\033[0m"
sleep 0.3
tree -L 2 --dirsfirst 2>/dev/null || find . -maxdepth 2 -type d | head -15
sleep 2

echo ""
echo -e "\033[1;36m── Memory ──\033[0m"
sleep 0.3
free -h
sleep 1

echo ""
echo -e "\033[1;36m── Disk ──\033[0m"
sleep 0.3
df -h /
sleep 1

echo ""
echo -e "\033[1;36m── Python ──\033[0m"
sleep 0.3
python3 -c "
import math
print(f'  Pi    = {math.pi:.10f}')
print(f'  e     = {math.e:.10f}')
print(f'  sqrt2 = {math.sqrt(2):.10f}')
print(f'  2^10  = {2**10}')
"
sleep 1.5

echo ""
echo -e "\033[1;36m── Date ──\033[0m"
sleep 0.3
date '+%Y-%m-%d %H:%M:%S %Z'
sleep 1

echo ""
echo -e "\033[1;36m── Network ──\033[0m"
sleep 0.3
ip -br addr 2>/dev/null || echo "(ip not available)"
sleep 1

echo ""
echo -e "\033[1;33m"
echo "╔═══════════════════════════════════════════════════╗"
echo "║           Recording Complete!                    ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "\033[0m"
sleep 1.5
SCRIPT
chmod +x "$DEMO_SCRIPT"

echo "=== STEP 3/7: Opening foot terminal with demo ==="
WAYLAND_DISPLAY=wayland-1 foot --maximized bash "$DEMO_SCRIPT" &
DEMO_PID=$!
sleep 1

echo "=== STEP 4/7: Starting wf-recorder (--no-dmabuf --no-damage) ==="
WAYLAND_DISPLAY=wayland-1 wf-recorder \
  -f "$RAW" \
  --no-dmabuf \
  --no-damage \
  -c libx264 \
  -r 25 \
  2>"$WF_LOG" &
REC_PID=$!
sleep 2

if ! kill -0 "$REC_PID" 2>/dev/null; then
  echo "FATAL: wf-recorder failed to start"
  cat "$WF_LOG"
  exit 1
fi

echo "Recording in progress..."

echo "=== STEP 5/7: Waiting for demo to finish ==="
wait $DEMO_PID 2>/dev/null || true
sleep 2

echo "=== STEP 6/7: Stopping recording ==="
timeout 5 kill $REC_PID 2>/dev/null || true
wait $REC_PID 2>/dev/null || true
sleep 1

RAW_SIZE=$(stat -c%s "$RAW" 2>/dev/null || echo 0)
echo "Raw capture: $RAW_SIZE bytes"

if [ "$RAW_SIZE" -lt 1000 ]; then
  echo "FATAL: Recording too small ($RAW_SIZE bytes)"
  exit 1
fi

# Get duration
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$RAW" 2>/dev/null || echo "30")
echo "Duration: ${DURATION}s"

echo "=== STEP 7/7: Encoding with VAAPI ==="
timeout 60 ffmpeg -y \
  -i "$RAW" \
  -vaapi_device /dev/dri/renderD128 \
  -vf "format=nv12,hwupload" \
  -c:v h264_vaapi -b:v 2M \
  -r 25 \
  "$ENCODED" \
  2>/tmp/ffmpeg-encode.log || {
    echo "VAAPI encoding failed, using raw capture as encoded"
    cp "$RAW" "$ENCODED"
  }

echo "=== Recording pipeline complete ==="
ls -lh "$ENCODED"
echo "Duration: $(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$ENCODED" 2>/dev/null)s"
