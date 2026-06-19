#!/bin/bash
# Complete example: Chrome + xdotool + recording
# Shows browser interaction visible on display

set -e

DISPLAY_NUM=99
RESOLUTION="608x1080"
OUTPUT="/tmp/chrome_demo.mp4"

echo "=== 1. Starting display :${DISPLAY_NUM} ==="
pkill -f "Xvfb :${DISPLAY_NUM}" 2>/dev/null || true
sleep 1
Xvfb ":${DISPLAY_NUM}" -screen 0 ${RESOLUTION}x24 &>/dev/null &
sleep 2
export DISPLAY=":${DISPLAY_NUM}"
echo "Display ready"

echo "=== 2. Launching Chrome ==="
pkill -9 chrome 2>/dev/null || true
sleep 1
google-chrome --no-sandbox --disable-gpu --window-size=608,1080 "https://github.com/trending" &>/dev/null &
CHROME_PID=$!
echo "Chrome PID: $CHROME_PID"
sleep 5

echo "=== 3. Starting recording ==="
ffmpeg -f x11grab -video_size 608x1080 -i ":${DISPLAY_NUM}.0" \
  -t 15 -g 30 -c:v libx264 -preset ultrafast -b:v 2M \
  -y "$OUTPUT" 2>/dev/null &
RECORD_PID=$!
echo "Recording PID: $RECORD_PID"

echo "=== 4. Interacting with browser ==="
echo "Scrolling..."
for i in 1 2 3 4 5; do
  xdotool key Down
  sleep 1
done

echo "Opening new tab..."
xdotool key ctrl+t
sleep 1

echo "Typing search..."
xdotool type "rust programming"
sleep 0.5
xdotool key Return
sleep 3

echo "Switching tabs..."
xdotool key ctrl+Tab
sleep 1

echo "More scrolling..."
for i in 1 2 3; do
  xdotool key Page_Down
  sleep 1
done

echo "=== 5. Stopping recording ==="
sleep 2
kill $RECORD_PID 2>/dev/null || true
sleep 1

echo "=== 6. Verifying ==="
if [ -f "$OUTPUT" ]; then
  SIZE=$(stat -c%s "$OUTPUT" 2>/dev/null)
  echo "Recording saved: $OUTPUT ($SIZE bytes)"
  ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration -of csv=p=0 "$OUTPUT"
else
  echo "Recording failed"
fi

echo "=== 7. Cleanup ==="
kill $CHROME_PID 2>/dev/null || true
pkill -f "Xvfb :${DISPLAY_NUM}" 2>/dev/null || true

echo ""
echo "=== DONE ==="
echo "View with: ffplay $OUTPUT"
echo "Or serve: python3 -m http.server 8080 -d /tmp"
