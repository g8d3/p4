#!/bin/bash
# capture_v2.sh - Record live resource monitoring comparison v2

set -euo pipefail

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="$WORKDIR/output"
mkdir -p "$OUTPUT"

# Kill any existing
pkill -f "Xvfb :99" 2>/dev/null || true
sleep 1

# 1. Start Xvfb
echo "=== Starting Xvfb ==="
Xvfb :99 -screen 0 608x1080x24 &
sleep 2

# 2. Open htop in xterm
echo "=== Opening htop ==="
DISPLAY=:99 xterm -geometry 80x24+5+5 -bg black -fg "#00ff88" -e htop &
sleep 1

# 3. Open GPU monitor in xterm
echo "=== Opening GPU monitor ==="
DISPLAY=:99 xterm -geometry 60x8+5+420 -bg black -fg "#00ccff" -e bash "$WORKDIR/gpu_monitor.sh" &
sleep 1

# 4. Start ffmpeg recording (90 seconds max)
echo "=== Starting recording ==="
DISPLAY=:99 ffmpeg -y \
    -f x11grab -video_size 608x1080 -i :99.0 \
    -framerate 15 -t 90 \
    -c:v libx264 -pix_fmt yuv420p -preset fast -b:v 1M \
    "$OUTPUT/comparison_live.mp4" &
FFMPEG_PID=$!
sleep 2

# 5. Run benchmarks while recording
echo "=== Running DeepSeek benchmark ==="
timeout 60 opencode run -m opencode-go/deepseek-v4-flash \
    "Write a Python function for merge sort with type hints." \
    > "$OUTPUT/deepseek_output.txt" 2>/dev/null || true

echo "=== Running MIMO benchmark ==="
timeout 60 opencode run -m opencode-go/mimo-v2.5 \
    "Write a Python function for merge sort with type hints." \
    > "$OUTPUT/mimo_output.txt" 2>/dev/null || true

echo "=== Waiting for recording to finish ==="
wait $FFMPEG_PID 2>/dev/null || true

# 6. Cleanup
echo "=== Cleanup ==="
pkill -f "Xvfb :99" 2>/dev/null || true
sleep 1

# 7. Verify
echo "=== Output ==="
ls -lh "$OUTPUT/comparison_live.mp4"
ffprobe "$OUTPUT/comparison_live.mp4" 2>&1 | grep -E "Duration|Stream"
echo "Done!"
