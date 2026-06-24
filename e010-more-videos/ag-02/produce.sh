#!/bin/bash
# produce.sh — Full pipeline: virtual display + monitoring + inference + narration + subtitles
# Output: output/final.mp4, output/metadata.json

set -euo pipefail

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="$WORKDIR/output"
mkdir -p "$OUTPUT/metrics" "$OUTPUT/gpu" "$OUTPUT/frames" "$OUTPUT/subs"

DISPLAY_NUM=":99"
RESOLUTION="608x1080"
RECORDING_SEC=120
BENCHMARK_TASK="Write a Python function that implements merge sort. Include docstring and type hints. Keep it concise but complete."

echo "=== STEP 1/8: Virtual display ==="
if ! DISPLAY=$DISPLAY_NUM xdpyinfo >/dev/null 2>&1; then
    timeout 5 Xvfb $DISPLAY_NUM -screen 0 ${RESOLUTION}x24 &>/dev/null &
    sleep 2
fi
echo "Display $DISPLAY_NUM ready at $RESOLUTION"

echo "=== STEP 2/8: Open monitoring terminals ==="
# htop — CPU/RAM monitor (top-left, fills ~40% height)
DISPLAY=$DISPLAY_NUM xterm \
    -geometry 60x20+0+0 \
    -bg "#0d1117" -fg "#00ff88" \
    -title "htop" \
    -e htop &
HTOP_PID=$!
sleep 1

# GPU monitor — radeontop (below htop)
DISPLAY=$DISPLAY_NUM xterm \
    -geometry 60x12+0+480 \
    -bg "#0d1117" -fg "#00ccff" \
    -title "gpu-monitor" \
    -e bash -c '
while true; do
    clear
    echo "=========================================="
    echo "        GPU RESOURCE MONITOR"
    echo "=========================================="
    timeout 1 radeontop -d - 2>/dev/null | tail -1 | tr "," "\n" | grep -E "gpu|vram|mclk|sclk" | sed "s/^ //"
    echo ""
    echo "=========================================="
    echo "        $(date "+%H:%M:%S")"
    echo "=========================================="
    sleep 2
done
' &
GPU_PID=$!
sleep 1

# Inference output terminal (bottom)
DISPLAY=$DISPLAY_NUM xterm \
    -geometry 60x14+0+700 \
    -bg "#0d1117" -fg "#f0e68c" \
    -title "inference" \
    -e bash -c 'echo "Waiting for inference..."; sleep 5; tail -f /dev/null' &
INF_TERM_PID=$!
sleep 1

echo "Monitoring terminals open (htop=$HTOP_PID, gpu=$GPU_PID)"

echo "=== STEP 3/8: Start GPU data collection ==="
GPU_CSV="$OUTPUT/gpu/gpu_metrics.csv"
echo "timestamp,gpu_percent,vram_used_mb,vram_total_mb,mclk_ghz,sclk_ghz" > "$GPU_CSV"
bash "$WORKDIR/collect_gpu_loop.sh" "$GPU_CSV" 2 &
GPU_COLLECT_PID=$!
sleep 2

echo "=== STEP 4/8: Start screen recording ==="
REC_VIDEO="$OUTPUT/screen_raw.mp4"
export LIBVA_DRIVER_NAME=radeonsi
timeout $((RECORDING_SEC + 10)) ffmpeg -y \
    -f x11grab -video_size $RESOLUTION -i $DISPLAY_NUM.0 \
    -framerate 15 \
    -c:v libx264 -pix_fmt yuv420p -preset fast -crf 23 \
    "$REC_VIDEO" &
FFMPEG_PID=$!
sleep 2
echo "Recording started (PID=$FFMPEG_PID)"

echo "=== STEP 5/8: Run provider benchmarks ==="
PROMPT="Write a Python function for merge sort with type hints."

echo "--- Benchmarking opencode-go/deepseek-v4-flash ---"
METRICS_DS="$OUTPUT/metrics/deepseek.json"
timeout 120 opencode run -m opencode-go/deepseek-v4-flash \
    "$PROMPT" \
    > "$OUTPUT/deepseek_output.txt" 2>/dev/null || true
# Parse metrics from the run
bash "$WORKDIR/parse_benchmark.sh" "$OUTPUT/deepseek_output.txt" "$METRICS_DS" "opencode-go/deepseek-v4-flash"
echo "DeepSeek done: $METRICS_DS"

echo "--- Benchmarking opencode-go/mimo-v2.5 ---"
METRICS_MM="$OUTPUT/metrics/mimo.json"
timeout 120 opencode run -m opencode-go/mimo-v2.5 \
    "$PROMPT" \
    > "$OUTPUT/mimo_output.txt" 2>/dev/null || true
bash "$WORKDIR/parse_benchmark.sh" "$OUTPUT/mimo_output.txt" "$METRICS_MM" "opencode-go/mimo-v2.5"
echo "MIMO done: $METRICS_MM"

echo "=== STEP 6/8: Stop recording + GPU monitor ==="
kill $GPU_COLLECT_PID 2>/dev/null || true
sleep 1
# Stop ffmpeg gracefully
kill $FFMPEG_PID 2>/dev/null || true
wait $FFMPEG_PID 2>/dev/null || true
echo "Recording stopped"

echo "=== STEP 7/8: Generate narration + subtitles ==="
# Generate narration from metrics
bash "$WORKDIR/make_narration.sh"
echo "Narration generated"

# Generate TikTok-style subtitles
python3 "$WORKDIR/make_subtitles.py" \
    "$OUTPUT/narration.mp3" \
    "$OUTPUT/narration.txt" \
    "$OUTPUT/subs/narration.srt"
echo "Subtitles generated"

echo "=== STEP 8/8: Compose final video ==="
bash "$WORKDIR/compose_final.sh"
echo "Final video composed"

# Cleanup monitoring terminals
kill $HTOP_PID $GPU_PID $INF_TERM_PID 2>/dev/null || true

# Generate metadata
bash "$WORKDIR/make_metadata.sh"

echo ""
echo "=== DONE ==="
ls -lh "$OUTPUT/final.mp4" 2>/dev/null || ls -lh "$OUTPUT/"*.mp4 2>/dev/null
echo "Metadata: $OUTPUT/metadata.json"
