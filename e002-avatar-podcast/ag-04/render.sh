#!/bin/bash
export LIBVA_DRIVER_NAME=radeonsi
START_TS=$(date +%s)

echo "=== STEP 1/3: Weston headless + Godot render to frames.raw ==="

weston --backend=headless --renderer=gl --socket=wayland-render --idle-time=0 --no-config 2>/dev/null &
WESTON_PID=$!
echo "Weston PID: $WESTON_PID"

for i in $(seq 1 10); do
  if [ -S "$XDG_RUNTIME_DIR/wayland-render" ]; then
    echo "Wayland socket ready after ${i}s"
    break
  fi
  sleep 1
done

FRAME_BYTES=$((608 * 1080 * 4))
TOTAL_FRAMES=6819
TOTAL_BYTES=$((FRAME_BYTES * TOTAL_FRAMES))

echo "=== Godot render loop: restart on crash/timeout until ${TOTAL_FRAMES} frames ==="
RESTART_COUNT=0
while true; do
  FSIZE=$(stat --format=%s frames.raw 2>/dev/null || echo 0)
  VALID_SIZE=$((FSIZE / FRAME_BYTES * FRAME_BYTES))
  if [ "$FSIZE" != "$VALID_SIZE" ]; then
    echo "Truncating partial frame: $FSIZE -> $VALID_SIZE"
    truncate -s "$VALID_SIZE" frames.raw 2>/dev/null || true
    FSIZE=$VALID_SIZE
  fi
  CUR_FRAMES=$((FSIZE / FRAME_BYTES))
  REMAINING=$((TOTAL_FRAMES - CUR_FRAMES))
  echo "--- frames.raw: ${CUR_FRAMES}/${TOTAL_FRAMES} frames (${REMAINING} remaining) ---"

  if [ "$CUR_FRAMES" -ge "$TOTAL_FRAMES" ]; then
    echo "All frames rendered!"
    break
  fi

  RESTART_COUNT=$((RESTART_COUNT + 1))
  echo "--- Godot run #${RESTART_COUNT} (frame ${CUR_FRAMES}) ---"

  WAYLAND_DISPLAY=wayland-render \
    timeout 45 ~/.local/bin/godot4 --display-driver wayland --rendering-driver opengl3 \
    --path godot_project -- config.json 2>&1 &
  GODOT_PID=$!

  while kill -0 $GODOT_PID 2>/dev/null; do
    ps -p $GODOT_PID -o %cpu= --no-headers >> /tmp/cpu_samples.txt 2>/dev/null
    cat /sys/class/drm/card*/device/gpu_busy_percent >> /tmp/gpu_samples.txt 2>/dev/null
    sleep 5
  done

  wait $GODOT_PID 2>/dev/null
  GODOT_EXIT=$?
  echo "--- Godot exit code ${GODOT_EXIT} ---"

  sleep 1
done

kill $WESTON_PID 2>/dev/null

echo "=== STEP 2/3: VAAPI encode frames.raw ==="
timeout 120 ffmpeg -f rawvideo -pix_fmt rgba -s 608x1080 -framerate 25 \
  -i frames.raw \
  -vf "format=nv12,hwupload" -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -y video_nosound.mp4
FRAMES_RAW_MB=$(stat --format=%s frames.raw 2>/dev/null | awk '{printf "%.0f", $1/1024/1024}')
rm -f frames.raw
END_TS=$(date +%s)

echo "=== STEP 3/3: Adding audio ==="
timeout 30 ffmpeg -i video_nosound.mp4 -i podcast_audio.mp3 \
  -c:v copy -c:a aac -shortest -y video.mp4

echo "=== Logging ==="
WALL_TIME=$((END_TS - START_TS))
VIDEO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 video.mp4)
FILE_MB=$(stat --format=%s video.mp4 | awk '{printf "%.1f", $1/1024/1024}')
TOTAL_FRAMES_ACTUAL=$(echo "$VIDEO_DUR * 25" | bc | cut -d. -f1)
RT_FACTOR=$(echo "scale=2; $VIDEO_DUR / $WALL_TIME" | bc)
CPU_AVG=$(awk '{sum+=$1; n++} END{printf "%.1f", sum/n}' /tmp/cpu_samples.txt 2>/dev/null || echo "0")
GPU_AVG=$(awk '{sum+=$1; n++} END{printf "%.1f", sum/n}' /tmp/gpu_samples.txt 2>/dev/null || echo "0")
CPU_PEAK=$(awk 'BEGIN{m=0}{if($1>m)m=$1}END{print m}' /tmp/cpu_samples.txt 2>/dev/null || echo "0")
GPU_PEAK=$(awk 'BEGIN{m=0}{if($1>m)m=$1}END{print m}' /tmp/cpu_samples.txt 2>/dev/null || echo "0")

echo "pipeline,wall_s,dur_s,fps,rt_factor,mb,frames,cpu_avg,gpu_avg,cpu_peak,gpu_peak,restarts,success" > render-log.csv
echo "pipe,$WALL_TIME,$VIDEO_DUR,25,$RT_FACTOR,$FILE_MB,$TOTAL_FRAMES_ACTUAL,$CPU_AVG,$GPU_AVG,$CPU_PEAK,$GPU_PEAK,$RESTART_COUNT,1" >> render-log.csv
rm -f /tmp/cpu_samples.txt /tmp/gpu_samples.txt
touch done.txt
echo "=== RENDER COMPLETE (${RESTART_COUNT} Godot runs) ==="

tmux send-keys -t a4 "Pipeline complete. video.mp4 $FILE_MB MB, ${VIDEO_DUR}s, rt_factor=$RT_FACTOR, runs=$RESTART_COUNT" Enter
