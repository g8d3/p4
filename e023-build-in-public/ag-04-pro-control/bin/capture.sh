#!/bin/bash
# E03 (Pro control) capture: wf-recorder on HEADLESS-2 + foot running driver.sh.
set -u
export TERM=xterm-256color
export SWAYSOCK=/run/user/1000/sway-ipc.1000.240699.sock
DIR=/home/vuos/code/p4/e023-build-in-public/ag-04-pro-control
DRIVER=$DIR/bin/driver.sh
CAP=$DIR/output/capture/raw_capture.mp4
WAYLAND_DISPLAY=wayland-1

echo "=== focus HEADLESS-2 + set 1920x1080 ==="
swaymsg output HEADLESS-2 resolution 1920x1080 >/dev/null 2>&1
swaymsg focus output HEADLESS-2 >/dev/null 2>&1
sleep 1
swaymsg -t get_outputs | python3 -c "import sys,json; d=json.load(sys.stdin); [print(o['name'], o.get('current_mode',{}).get('width'),'x',o.get('current_mode',{}).get('height'),'focus=',o.get('focused')) for o in d if o['name']=='HEADLESS-2']"

# orphan check: any wf-recorder on HEADLESS-2 already?
pgrep -a wf-recorder

rm -f "$CAP"

echo "=== starting wf-recorder on HEADLESS-2 ==="
WAYLAND_DISPLAY=$WAYLAND_DISPLAY wf-recorder \
  -o HEADLESS-2 \
  -f "$CAP" \
  --no-dmabuf \
  --no-damage \
  -c libx264 \
  -r 25 \
  -p crf=23 \
  -p preset=veryfast \
  2>/tmp/opencode/e03-wf-recorder.log &
REC_PID=$!
sleep 3

if ! kill -0 "$REC_PID" 2>/dev/null; then
  echo "FATAL: wf-recorder failed"; cat /tmp/opencode/e03-wf-recorder.log; exit 1
fi
echo "wf-recorder running (PID=$REC_PID)"

echo "=== launching foot with driver ==="
WAYLAND_DISPLAY=$WAYLAND_DISPLAY foot --maximized --font=monospace:size=24 bash "$DRIVER" \
  > /tmp/opencode/e03-foot-driver.log 2>&1 &
FOOT_PID=$!

# guarantee the foot window lands on HEADLESS-2 (focus can be racy)
sleep 1
swaymsg '[app_id="foot"] move container to output HEADLESS-2' >/dev/null 2>&1
swaymsg -t get_tree | python3 -c "
import sys,json
d=json.load(sys.stdin)
def walk(n):
    if n.get('app_id')=='foot':
        print('foot output:', n.get('output'), 'rect:', n.get('rect'))
    for c in n.get('nodes',[])+n.get('floating_nodes',[]):
        walk(c)
walk(d)"

echo "REC_PID=$REC_PID" > /tmp/opencode/e03-capture-state.env
echo "FOOT_PID=$FOOT_PID" >> /tmp/opencode/e03-capture-state.env
echo "capture started at $(date +%H:%M:%S)"

# wait for the driver (foot process) to finish, then stop the recorder
while kill -0 "$FOOT_PID" 2>/dev/null; do
  sleep 2
done
echo "driver finished; stopping recorder"
sleep 2
kill "$REC_PID" 2>/dev/null
sleep 2
echo "=== capture done ==="
ffprobe -v error -show_entries format=duration -of csv=p=0 "$CAP" 2>/dev/null
