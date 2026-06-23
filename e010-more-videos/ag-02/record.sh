#!/bin/bash
# record.sh - Main orchestrator for resource monitoring comparison video
# Sets up virtual display, runs benchmarks, captures GPU, renders dashboard, records video

set -euo pipefail

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="$WORKDIR/output"
METRICS_DIR="$OUTPUT_DIR/metrics"
GPU_DIR="$OUTPUT_DIR/gpu"
FRAMES_DIR="$OUTPUT_DIR/frames"
VIDEO_FILE="$OUTPUT_DIR/comparison.mp4"

# Benchmark task - something that generates consistent tokens
BENCHMARK_TASK="Write a Python function that implements merge sort. Include docstring and type hints. Keep it concise but complete."

# Display settings
DISPLAY_NUM=":99"
RESOLUTION="608x1080"

echo "=== Resource Monitoring Comparison ==="
echo "Working directory: $WORKDIR"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Create output directories
mkdir -p "$METRICS_DIR" "$GPU_DIR" "$FRAMES_DIR"

# Step 1: Verify virtual display
echo "=== STEP 1/6: Verifying virtual display ==="
if ! DISPLAY=$DISPLAY_NUM xdpyinfo >/dev/null 2>&1; then
    echo "Starting Xvfb on $DISPLAY_NUM..."
    timeout 5 Xvfb $DISPLAY_NUM -screen 0 ${RESOLUTION}x24 &>/dev/null &
    sleep 1
fi
echo "Display $DISPLAY_NUM ready at $RESOLUTION"

# Step 2: Start GPU monitoring
echo "=== STEP 2/6: Starting GPU monitoring ==="
GPU_CSV="$GPU_DIR/gpu_metrics.csv"
bash "$WORKDIR/monitor_gpu.sh" "$GPU_CSV" 1 &
GPU_MONITOR_PID=$!
echo "GPU monitor PID: $GPU_MONITOR_PID"
sleep 2  # Let it collect a few samples

# Step 3: Run benchmarks on both providers
echo "=== STEP 3/6: Benchmarking opencode-go/deepseek-v4-flash ==="
METRICS_LEFT="$METRICS_DIR/deepseek.json"
bash "$WORKDIR/run_benchmark.sh" "opencode-go/deepseek-v4-flash" "$BENCHMARK_TASK" "$METRICS_LEFT"

echo ""
echo "=== STEP 4/6: Benchmarking opencode-go/mimo-v2.5 ==="
METRICS_RIGHT="$METRICS_DIR/mimo.json"
bash "$WORKDIR/run_benchmark.sh" "opencode-go/mimo-v2.5" "$BENCHMARK_TASK" "$METRICS_RIGHT"

# Step 4: Stop GPU monitoring
echo ""
echo "=== Stopping GPU monitor ==="
kill $GPU_MONITOR_PID 2>/dev/null || true
wait $GPU_MONITOR_PID 2>/dev/null || true

# Step 5: Render dashboard frames
echo ""
echo "=== STEP 5/6: Rendering dashboard frames ==="
# Get GPU data line count for frame count
GPU_LINES=$(wc -l < "$GPU_CSV" 2>/dev/null || echo "10")
TOTAL_FRAMES=$((GPU_LINES * 5))  # ~5 seconds per GPU sample at 1fps
TOTAL_FRAMES=$((TOTAL_FRAMES > 90 ? TOTAL_FRAMES : 90))  # At least 3 seconds
TOTAL_FRAMES=$((TOTAL_FRAMES < 300 ? TOTAL_FRAMES : 300))  # Cap at 10 seconds

python3 "$WORKDIR/render_dashboard.py" "$METRICS_LEFT" "$METRICS_RIGHT" "$GPU_CSV" "$FRAMES_DIR" "$TOTAL_FRAMES"

# Step 6: Encode video with ffmpeg
echo ""
echo "=== STEP 6/6: Encoding video ==="
export LIBVA_DRIVER_NAME=radeonsi
timeout 60 ffmpeg -y \
    -framerate 30 \
    -i "$FRAMES_DIR/frame_%04d.png" \
    -vf "format=nv12,hwupload" \
    -c:v h264_vaapi \
    -b:v 2M \
    -pix_fmt yuv420p \
    "$VIDEO_FILE" 2>/dev/null || \
timeout 60 ffmpeg -y \
    -framerate 30 \
    -i "$FRAMES_DIR/frame_%04d.png" \
    -c:v libx264 \
    -pix_fmt yuv420p \
    -b:v 2M \
    "$VIDEO_FILE" 2>/dev/null

# Verify output
echo ""
echo "=== Verification ==="
if [ -f "$VIDEO_FILE" ]; then
    SIZE=$(stat -c%s "$VIDEO_FILE" 2>/dev/null || stat -f%z "$VIDEO_FILE" 2>/dev/null || echo "0")
    DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$VIDEO_FILE" 2>/dev/null || echo "0")
    echo "Video: $VIDEO_FILE"
    echo "Size: $(( SIZE / 1024 )) KB"
    echo "Duration: ${DURATION}s"
    echo "Resolution: $RESOLUTION"
else
    echo "ERROR: Video not created!"
fi

# Cleanup frames
echo ""
echo "Cleaning up frames..."
rm -rf "$FRAMES_DIR"

echo ""
echo "=== Done ==="
echo "Metrics saved to: $METRICS_DIR/"
echo "Video saved to: $VIDEO_FILE"
