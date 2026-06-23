#!/bin/bash
# capture.sh - Record live resource monitoring comparison
# Records screen with htop + GPU monitor while running benchmarks

set -x

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="$WORKDIR/output"
mkdir -p "$OUTPUT"

# Clean up any existing processes
pkill -f "Xvfb :99" 2>/dev/null || true
pkill -f "xterm.*:99" 2>/dev/null || true
sleep 1

# Step 1: Start Xvfb
echo "=== Starting Xvfb ==="
Xvfb :99 -screen 0 608x1080x24 &
XVFB_PID=$!
sleep 2
echo "Xvfb PID: $XVFB_PID"

# Step 2: Open xterm with htop
echo "=== Opening htop ==="
DISPLAY=:99 xterm -geometry 80x25+10+10 -bg "#1a1a2e" -fg "#00ff88" -title "htop" -e htop &
HTOP_PID=$!
sleep 1

# Step 3: Open xterm with GPU monitor
echo "=== Opening GPU monitor ==="
DISPLAY=:99 xterm -geometry 80x10+10+500 -bg "#1a1a2e" -fg "#00ccff" -title "gpu-monitor" -e bash -c '
while true; do
    clear
    echo "╔══════════════════════════════════════╗"
    echo "║       GPU RESOURCE MONITOR           ║"
    echo "╠══════════════════════════════════════╣"
    radeontop -d - 2>/dev/null | tail -1 | awk -F", " "{
        for(i=1;i<=NF;i++) {
            if($i ~ /gpu/) printf "║ GPU:  %-29s ║\n", $i
            if($i ~ /vram/) printf "║ VRAM: %-29s ║\n", $i
            if($i ~ /mclk/) printf "║ MCLK: %-29s ║\n", $i
            if($i ~ /sclk/) printf "║ SCLK: %-29s ║\n", $i
        }
    }"
    echo "╚══════════════════════════════════════╝"
    sleep 2
done
' &
GPU_PID=$!
sleep 1

# Step 4: Start ffmpeg recording (60 seconds max)
echo "=== Starting ffmpeg recording ==="
DISPLAY=:99 ffmpeg -y \
    -f x11grab -video_size 608x1080 -i :99.0 \
    -framerate 15 -t 90 \
    -c:v libx264 -pix_fmt yuv420p -preset fast -b:v 1M \
    "$OUTPUT/comparison_live.mp4" &
FFMPEG_PID=$!
sleep 2

# Step 5: Run benchmarks (while recording)
echo "=== Running DeepSeek benchmark ==="
opencode run -m opencode-go/deepseek-v4-flash \
    "Write a Python function for merge sort with type hints." \
    > "$OUTPUT/deepseek_output.txt" 2>/dev/null

echo "=== Running MIMO benchmark ==="
opencode run -m opencode-go/mimo-v2.5 \
    "Write a Python function for merge sort with type hints." \
    > "$OUTPUT/mimo_output.txt" 2>/dev/null

echo "=== Benchmarks done, waiting for recording to finish ==="
# Wait for ffmpeg to finish (max 90s recording)
wait $FFMPEG_PID 2>/dev/null || true

# Step 6: Cleanup
echo "=== Cleaning up ==="
kill $HTOP_PID $GPU_PID $XVFB_PID 2>/dev/null || true
pkill -f "Xvfb :99" 2>/dev/null || true

# Verify output
echo "=== Output ==="
ls -lh "$OUTPUT/comparison_live.mp4"
ffprobe "$OUTPUT/comparison_live.mp4" 2>&1 | grep -E "Duration|Stream|Video"
