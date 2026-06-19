#!/bin/bash
# Example: Control google-chrome with xdotool on a real display
# This demonstrates browser automation visible on Xvfb or real display

set -e

# --- Configuration ---
DISPLAY_NUM="${1:-99}"
RESOLUTION="608x1080"
URL="https://github.com/trending"

echo "=== Step 1: Start Xvfb display :${DISPLAY_NUM} ==="
# Kill existing Xvfb on this display
pkill -f "Xvfb :${DISPLAY_NUM}" 2>/dev/null || true
sleep 1

# Start Xvfb
Xvfb ":${DISPLAY_NUM}" -screen 0 ${RESOLUTION}x24 &>/dev/null &
XVFB_PID=$!
sleep 2

export DISPLAY=":${DISPLAY_NUM}"
echo "Display :${DISPLAY_NUM} started (PID=$XVFB_PID)"

echo "=== Step 2: Launch google-chrome ==="
# Kill existing Chrome
pkill -9 chrome 2>/dev/null || true
sleep 1

# Launch Chrome
google-chrome \
  --no-sandbox \
  --disable-gpu \
  --window-size=608,1080 \
  --start-maximized \
  "$URL" &>/dev/null &
CHROME_PID=$!
echo "Chrome launched (PID=$CHROME_PID)"

# Wait for Chrome to load
echo "Waiting for Chrome to load..."
sleep 5

echo "=== Step 3: Verify Chrome is running ==="
if pgrep -x chrome > /dev/null; then
  echo "✓ Chrome is running"
else
  echo "✗ Chrome failed to start"
  exit 1
fi

echo "=== Step 4: Take screenshot to verify ==="
import -window root /tmp/screen_before.png 2>/dev/null || \
  xwd -root -out /tmp/screen_before.xwd 2>/dev/null && \
  convert /tmp/screen_before.xwd /tmp/screen_before.png 2>/dev/null || \
  echo "Screenshot tools not available, skipping"

echo "=== Step 5: Interact with browser using xdotool ==="

# Scroll down 3 times
echo "Scrolling down..."
for i in 1 2 3; do
  xdotool key Down
  sleep 0.5
done

# Open new tab
echo "Opening new tab (Ctrl+T)..."
xdotool key ctrl+t
sleep 1

# Type a search query
echo "Typing search query..."
xdotool type "rust programming language"
sleep 0.5

# Press Enter
echo "Pressing Enter..."
xdotool key Return
sleep 3

# Switch back to first tab
echo "Switching to first tab..."
xdotool key ctrl+Tab
sleep 1

# Scroll more
echo "Scrolling more..."
for i in 1 2 3 4 5; do
  xdotool key Page_Down
  sleep 0.5
done

echo "=== Step 6: Take screenshot after interaction ==="
import -window root /tmp/screen_after.png 2>/dev/null || \
  xwd -root -out /tmp/screen_after.xwd 2>/dev/null && \
  convert /tmp/screen_after.xwd /tmp/screen_after.png 2>/dev/null || \
  echo "Screenshot tools not available, skipping"

echo "=== Step 7: Record 10 seconds of browser interaction ==="
timeout 15 ffmpeg -f x11grab -video_size 608x1080 -i ":${DISPLAY_NUM}.0" \
  -t 10 -g 30 -keyint_min 30 \
  -c:v libx264 -preset ultrafast -b:v 2M \
  -y /tmp/browser_demo.mp4 2>/dev/null

echo "=== Step 8: Verify recording ==="
if [ -f /tmp/browser_demo.mp4 ]; then
  SIZE=$(stat -c%s /tmp/browser_demo.mp4 2>/dev/null || stat -f%z /tmp/browser_demo.mp4 2>/dev/null)
  echo "✓ Recording saved: /tmp/browser_demo.mp4 ($SIZE bytes)"
  ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration -of csv=p=0 /tmp/browser_demo.mp4
else
  echo "✗ Recording failed"
fi

echo "=== Step 9: Cleanup ==="
kill $CHROME_PID 2>/dev/null || true
kill $XVFB_PID 2>/dev/null || true
pkill -f "Xvfb :${DISPLAY_NUM}" 2>/dev/null || true

echo ""
echo "=== DONE ==="
echo "Files created:"
echo "  - /tmp/screen_before.png (before interaction)"
echo "  - /tmp/screen_after.png (after interaction)"
echo "  - /tmp/browser_demo.mp4 (10s recording)"
echo ""
echo "To view on real display, run without Xvfb:"
echo "  DISPLAY=:0 $0 0"
