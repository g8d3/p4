#!/bin/bash
# Minimal example: Launch Chrome on display and interact
# Run: ./launch_chrome.sh [display_number]

DISPLAY_NUM="${1:-99}"

echo "Starting Chrome on display :${DISPLAY_NUM}..."

# Start Xvfb if not using real display
if [ "$DISPLAY_NUM" != "0" ]; then
  pkill -f "Xvfb :${DISPLAY_NUM}" 2>/dev/null || true
  sleep 1
  Xvfb ":${DISPLAY_NUM}" -screen 0 608x1080x24 &>/dev/null &
  sleep 2
fi

export DISPLAY=":${DISPLAY_NUM}"

# Kill existing Chrome
pkill -9 chrome 2>/dev/null || true
sleep 1

# Launch Chrome
google-chrome \
  --no-sandbox \
  --disable-gpu \
  --window-size=608,1080 \
  "https://github.com/trending" &

CHROME_PID=$!
echo "Chrome launched (PID=$CHROME_PID)"
echo "Display: :${DISPLAY_NUM}"
echo ""
echo "To interact, use xdotool:"
echo "  xdotool key Down          # scroll down"
echo "  xdotool key ctrl+t        # new tab"
echo "  xdotool type 'search'     # type text"
echo "  xdotool key Return        # press Enter"
echo ""
echo "Press Ctrl+C to stop"
wait $CHROME_PID
