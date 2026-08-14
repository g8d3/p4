#!/bin/bash
# E02 capture: wf-recorder on HEADLESS-1 + foot running ep2_driver.sh.
set -u
export TERM=xterm-256color
DRIVER=/home/vuos/code/p4/e023-build-in-public/ag-01/bin/ep2_driver.sh
CAP=/home/vuos/code/p4/e023-build-in-public/ag-01/output/capture/ep2_raw_capture.mp4
WAYLAND_DISPLAY=wayland-1

rm -f "$CAP"

echo "=== starting wf-recorder on HEADLESS-1 ==="
WAYLAND_DISPLAY=$WAYLAND_DISPLAY wf-recorder \
  -o HEADLESS-1 \
  -f "$CAP" \
  --no-dmabuf \
  --no-damage \
  -c libx264 \
  -r 25 \
  -p crf=23 \
  -p preset=veryfast \
  2>/tmp/opencode/ep2-wf-recorder.log &
REC_PID=$!
sleep 3

if ! kill -0 "$REC_PID" 2>/dev/null; then
  echo "FATAL: wf-recorder failed"; cat /tmp/opencode/ep2-wf-recorder.log; exit 1
fi
echo "wf-recorder running (PID=$REC_PID)"

echo "=== launching foot with driver ==="
WAYLAND_DISPLAY=$WAYLAND_DISPLAY foot --maximized --font=monospace:size=17 bash "$DRIVER" \
  > /tmp/opencode/ep2-foot-driver.log 2>&1 &
FOOT_PID=$!

echo "REC_PID=$REC_PID" > /tmp/opencode/ep2-capture-state.env
echo "FOOT_PID=$FOOT_PID" >> /tmp/opencode/ep2-capture-state.env
echo "capture started at $(date +%H:%M:%S)"
