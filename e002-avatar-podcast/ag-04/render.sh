#!/bin/bash
set -e
export LIBVA_DRIVER_NAME=radeonsi
START_TS=$(date +%s)

# Clean previous artifacts
rm -f video_raw.avi video_nosound.mp4 video.mp4 done.txt
rm -f /tmp/render_pipe /tmp/cpu_samples.txt /tmp/gpu_samples.txt
mkfifo /tmp/render_pipe

echo "=== STEP 1/4: ffmpeg VAAPI capture ==="
timeout 600 ffmpeg -f rawvideo -pix_fmt rgba -s 608x1080 -framerate 25 -i /tmp/render_pipe \
  -vf "format=nv12,hwupload" -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -y video_nosound.mp4 &
FFPID=$!

echo "=== STEP 2/4: Godot render (Weston+Wayland+Vulkan) ==="
weston --backend=headless --renderer=gl --socket=wayland-render 2>/dev/null &
sleep 2
WAYLAND_DISPLAY=wayland-render \
  timeout 600 ~/.local/bin/godot4 --display-driver wayland --rendering-driver vulkan \
  --path godot_project -- config.json &
GODOT_PID=$!

# Sample CPU/GPU while Godot runs
(while kill -0 $GODOT_PID 2>/dev/null; do
  echo "=== Godot PID $GODOT_PID running... ==="
  ps -p $GODOT_PID -o %cpu= --no-headers >> /tmp/cpu_samples.txt 2>/dev/null
  cat /sys/class/drm/card*/device/gpu_busy_percent >> /tmp/gpu_samples.txt 2>/dev/null
  sleep 5
done) &

wait $GODOT_PID 2>/dev/null
echo "=== STEP 3/4: Godot finished, stopping capture ==="
wait $FFPID 2>/dev/null
rm -f /tmp/render_pipe
END_TS=$(date +%s)

echo "=== STEP 4/4: Adding audio ==="
timeout 30 ffmpeg -i video_nosound.mp4 -i podcast_audio.mp3 -c:v copy -c:a aac -shortest -y video.mp4

echo "=== Logging ==="
WALL_TIME=$((END_TS - START_TS))
VIDEO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 video.mp4)
FILE_MB=$(stat --format=%s video.mp4 | awk '{printf "%.1f", $1/1024/1024}')
TOTAL_FRAMES=$(echo "$VIDEO_DUR * 25" | bc | cut -d. -f1)
RT_FACTOR=$(echo "scale=2; $VIDEO_DUR / $WALL_TIME" | bc)
CPU_AVG=$(awk '{sum+=$1; n++} END{printf "%.1f", sum/n}' /tmp/cpu_samples.txt 2>/dev/null || echo "0")
GPU_AVG=$(awk '{sum+=$1; n++} END{printf "%.1f", sum/n}' /tmp/gpu_samples.txt 2>/dev/null || echo "0")
CPU_PEAK=$(awk 'BEGIN{m=0}{if($1>m)m=$1}END{print m}' /tmp/cpu_samples.txt 2>/dev/null || echo "0")
GPU_PEAK=$(awk 'BEGIN{m=0}{if($1>m)m=$1}END{print m}' /tmp/gpu_samples.txt 2>/dev/null || echo "0")

echo "pipeline,wall_s,dur_s,fps,rt_factor,mb,frames,cpu_avg,gpu_avg,cpu_peak,gpu_peak,success" > render-log.csv
echo "pipe,$WALL_TIME,$VIDEO_DUR,25,$RT_FACTOR,$FILE_MB,$TOTAL_FRAMES,$CPU_AVG,$GPU_AVG,$CPU_PEAK,$GPU_PEAK,1" >> render-log.csv
rm -f /tmp/cpu_samples.txt /tmp/gpu_samples.txt /tmp/render_pipe
touch done.txt
echo "=== RENDER COMPLETE ==="

# Wake the agent one last time
tmux send-keys -t a4 "Pipeline complete. done.txt created." Enter
