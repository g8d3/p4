#!/bin/bash
# Orchestrates: Sway headless -> wf-recorder -> foot terminal demo -> cleanup
# Records VIDEO ONLY — audio is mixed in post for precise timing/silence control.
set -e

BASE="/home/vuos/code/p4/e010-more-videos/ag-03"
XDG_RT="/run/user/1000"
export XDG_RUNTIME_DIR="$XDG_RT"
export WLR_BACKENDS=headless
export WLR_LIBINPUT_NO_DEVICES=1
export LIBVA_DRIVER_NAME=radeonsi
export WAYLAND_DISPLAY="wayland-7"

rm -f "$XDG_RT/$WAYLAND_DISPLAY" "$XDG_RT/${WAYLAND_DISPLAY}.lock" 2>/dev/null || true

echo "=== Starting Sway headless (608x1080) ==="
sway -c "$BASE/bin/sway-headless.conf" >/dev/null 2>&1 &
SWAY_PID=$!
sleep 3

if ! kill -0 $SWAY_PID 2>/dev/null; then
    echo "ERROR: Sway failed to start"
    exit 1
fi

# Find IPC socket
SWAYSOCK=$(ls "$XDG_RT"/sway-ipc.* 2>/dev/null | sort -t. -k4 -n | tail -1)
export SWAYSOCK
echo "SWAYSOCK=$SWAYSOCK"

# Find Wayland display socket (Sway may use a different name)
if [ ! -S "$XDG_RT/$WAYLAND_DISPLAY" ]; then
    NEWEST=$(ls -t "$XDG_RT"/wayland-* 2>/dev/null | head -1)
    if [ -n "$NEWEST" ]; then
        WAYLAND_DISPLAY=$(basename "$NEWEST")
        export WAYLAND_DISPLAY
    fi
fi
echo "WAYLAND_DISPLAY=$WAYLAND_DISPLAY"

echo "=== Verifying output ==="
SWAYSOCK="$SWAYSOCK" swaymsg -t get_outputs 2>/dev/null | python3 -c "
import sys, json
for o in json.load(sys.stdin):
    m = o.get('current_mode', {})
    print(f\"  {o['name']}: {m.get('width','?')}x{m.get('height','?')}\")
"

echo "=== Starting wf-recorder (video, 15fps, VAAPI) ==="
REC_START=$(date +%s.%N)
WAYLAND_DISPLAY="$WAYLAND_DISPLAY" wf-recorder \
    -o HEADLESS-1 \
    -D \
    -r 15 \
    -c h264_vaapi \
    -d /dev/dri/renderD128 \
    -f "$BASE/output/recording_raw.mp4" >/dev/null 2>&1 &
REC_PID=$!

sleep 2

echo "=== Starting foot terminal with demo ==="
DEMO_START=$(date +%s.%N)
WAYLAND_DISPLAY="$WAYLAND_DISPLAY" foot \
    -f "monospace:size=14" \
    -w 608x1080 \
    -F \
    bash "$BASE/bin/demo.sh" >/dev/null 2>&1 &
FOOT_PID=$!

echo "=== Waiting for demo (max 120s) ==="
ELAPSED=0
while kill -0 $FOOT_PID 2>/dev/null && [ $ELAPSED -lt 120 ]; do
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    [ $((ELAPSED % 10)) -eq 0 ] && echo "  ... ${ELAPSED}s"
done
REC_END=$(date +%s.%N)

echo "=== Stopping ==="
kill -INT $REC_PID 2>/dev/null || true
sleep 2
kill $FOOT_PID 2>/dev/null || true
SWAYSOCK="$SWAYSOCK" swaymsg exit 2>/dev/null || true
sleep 1
kill $SWAY_PID 2>/dev/null || true

# Save offset (recording starts before demo)
python3 -c "
import json
data = {
    'rec_start': $REC_START,
    'demo_start': $DEMO_START,
    'offset_sec': $DEMO_START - $REC_START,
    'rec_end': $REC_END,
}
with open('$BASE/assets/record_timing.json', 'w') as f:
    json.dump(data, f, indent=2)
print(f\"Recording offset: {data['offset_sec']:.2f}s\")
"

echo ""
echo "=== RESULT ==="
if [ -f "$BASE/output/recording_raw.mp4" ]; then
    ls -lh "$BASE/output/recording_raw.mp4"
    ffprobe -v error -show_entries format=duration,size \
        -show_entries stream=codec_name,width,height,r_frame_rate \
        -of json "$BASE/output/recording_raw.mp4" 2>&1
else
    echo "ERROR: No recording!"
    exit 1
fi
