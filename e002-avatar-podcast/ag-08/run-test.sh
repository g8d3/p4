#!/bin/bash
set -e

echo "=== Step 1: Clean ==="
timeout 3 pkill -f weston-simple-egl 2>/dev/null || true
timeout 3 pkill -f wf-recorder 2>/dev/null || true
timeout 3 pkill -f "sway" 2>/dev/null || true
rm -f /home/vuos/code/p4/e002-avatar-podcast/ag-08/test_output.mp4
sleep 1

echo "=== Step 2: Start Sway headless ==="
WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 sway &
SWAY_PID=$!
sleep 3

echo "=== Step 3: Open colored window ==="
WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 timeout 8 weston-simple-egl &
SIMPLE_PID=$!
sleep 2

echo "=== Step 4: Record with wf-recorder VAAPI ==="
WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 timeout 8 \
  wf-recorder -f /home/vuos/code/p4/e002-avatar-podcast/ag-08/test_output.mp4 \
  -c h264_vaapi -b 2M 2>&1 || true

echo "=== Step 5: Verify ==="
ls -lh /home/vuos/code/p4/e002-avatar-podcast/ag-08/test_output.mp4 2>/dev/null || echo "NO_FILE"
echo "=== GPU ==="
cat /sys/class/drm/card*/device/gpu_busy_percent 2>/dev/null || echo "N/A"

echo "=== Step 6: ffprobe ==="
ffprobe /home/vuos/code/p4/e002-avatar-podcast/ag-08/test_output.mp4 2>&1 | grep -i "Stream\|Duration" || echo "NO_PROBE"

echo "=== DONE ==="
timeout 3 kill $SIMPLE_PID 2>/dev/null || true
timeout 3 kill $SWAY_PID 2>/dev/null || true
