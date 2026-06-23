#!/bin/bash
export DISPLAY=:99

pkill -f "xterm" 2>/dev/null || true
sleep 1

# Start xterm
xterm -geometry 60x45+0+0 -bg black -fg "#00ff88" -fa "Mono" -fs 14 &
XPID=$!
sleep 2

# Get window ID from xwininfo
WID=$(xwininfo -root -tree 2>/dev/null | grep -oP '0x[0-9a-f]+.*xterm' | head -1 | grep -oP '0x[0-9a-f]+')
echo "WID=$WID XPID=$XPID"

# Start ffmpeg
export LIBVA_DRIVER_NAME=radeonsi
timeout 55 ffmpeg -f x11grab -video_size 608x1080 -i :99.0 \
  -vaapi_device /dev/dri/renderD128 \
  -vf "format=nv12,hwupload" \
  -c:v h264_vaapi -r 15 -t 30 \
  -y /home/vuos/code/p4/e010-more-videos/ag-01/output/recording.mp4 \
  2>/tmp/ffmpeg-ag01.log &
FFPID=$!
sleep 2

# Type commands
type_cmd() {
  xdotool key --window $WID ctrl+c 2>/dev/null || true
  sleep 0.05
  xdotool type --window $WID --delay 8 "$1" 2>/dev/null
  xdotool key --window $WID Return 2>/dev/null
  sleep 0.15
}

type_cmd "echo '==============================================='"
type_cmd "echo '  ag-01: Virtual Display Recording Pipeline   '"
type_cmd "echo '  Xvfb :99  608x1080  H.264 VAAPI            '"
type_cmd "echo '==============================================='"
type_cmd "echo ''"
type_cmd "echo '--- System ---'"
type_cmd "uname -a"
type_cmd "echo ''"
type_cmd "echo '--- Date ---'"
type_cmd "date"
type_cmd "echo ''"
type_cmd "echo '--- Uptime ---'"
type_cmd "uptime"
type_cmd "echo ''"
type_cmd "echo '--- Memory ---'"
type_cmd "free -h"
type_cmd "echo ''"
type_cmd "echo '--- Disk ---'"
type_cmd "df -h /"
type_cmd "echo ''"
type_cmd "echo '--- Top processes ---'"
type_cmd "ps aux --sort=-%cpu | head -6"
type_cmd "echo ''"
type_cmd "echo '--- Files ---'"
type_cmd "ls -la /home/vuos/code/p4/e010-more-videos/ag-01/"
type_cmd "echo ''"
type_cmd "echo '--- Python calc ---'"
type_cmd "python3 -c \"print('Pi:', 3.14159265358979)\""
type_cmd "echo ''"
type_cmd "echo '==============================================='"
type_cmd "echo '  Recording complete!                          '"
type_cmd "echo '==============================================='"
sleep 3

kill $FFPID 2>/dev/null || true
wait $FFPID 2>/dev/null || true

ls -lh /home/vuos/code/p4/e010-more-videos/ag-01/output/recording.mp4
echo "DONE"
