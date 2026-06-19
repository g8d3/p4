# Browser Control Example

Example of controlling `google-chrome` with `xdotool` on a real display.

## Quick Start

```bash
# Run on virtual display :99
./browser_example.sh 99

# Run on real display :0 (your actual monitor)
sudo ./browser_example.sh 0
```

## What it demonstrates

1. **Start Xvfb** virtual display (608×1080 vertical)
2. **Launch Chrome** with a URL
3. **Interact** with xdotool:
   - Scroll down (`key Down`)
   - Open new tab (`ctrl+t`)
   - Type text (`type "query"`)
   - Press Enter (`key Return`)
   - Switch tabs (`ctrl+Tab`)
   - Page down (`key Page_Down`)
4. **Record** 10 seconds of interaction
5. **Verify** the recording

## Prerequisites

```bash
# Install required tools
sudo apt-get install -y xdotool imagemagick xvfb ffmpeg

# For real display (Wayland/Sway)
sudo apt-get install -y ydotool
```

## Key commands

| Action | xdotool command |
|--------|-----------------|
| Scroll down | `xdotool key Down` |
| Page down | `xdotool key Page_Down` |
| Open new tab | `xdotool key ctrl+t` |
| Switch tab | `xdotool key ctrl+Tab` |
| Type text | `xdotool type "hello"` |
| Press Enter | `xdotool key Return` |
| Click at position | `xdotool mousemove 300 540 click 1` |

## Viewing on real display

To see Chrome on your actual monitor:

```bash
# Option 1: Use existing display
DISPLAY=:0 google-chrome --no-sandbox https://github.com/trending

# Option 2: Start Xvfb and connect VNC
Xvfb :99 -screen 0 608x1080x24 &
DISPLAY=:99 google-chrome --no-sandbox https://github.com/trending &
x11vnc -display :99 -forever &
# Connect with VNC client to localhost:5900
```

## Files created

- `/tmp/screen_before.png` — screenshot before interaction
- `/tmp/screen_after.png` — screenshot after interaction  
- `/tmp/browser_demo.mp4` — 10-second recording
