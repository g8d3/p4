# ag-04 — Video composer

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, self-wake pattern

## Model
`opencode-go/mimo-v2.5` (use with `-m` flag)

## Goal

Compose the podcast video using the minimal GPU pipeline: Godot renders frames to `frames.raw`, ffmpeg encodes with VAAPI (GPU). No CPU encoding.

## Pipeline (exact commands)

### 1. Clean and prepare
```
rm -f frames.raw video_nosound.mp4 video.mp4 done.txt
export LIBVA_DRIVER_NAME=radeonsi
```

### 2. Start timer and CPU/GPU sampler
```
START_TS=$(date +%s)
echo "" > /tmp/cpu_samples.txt; echo "" > /tmp/gpu_samples.txt
```

### 3. Render with Godot (background + self-wake)
```
timeout 600 ~/.local/bin/godot4 --rendering-driver vulkan --display-driver headless \
  --path godot_project -- config.json &
GODOT_PID=$!

# Sample CPU/GPU in background while Godot runs
(while kill -0 $GODOT_PID 2>/dev/null; do
  ps -p $GODOT_PID -o %cpu= --no-headers >> /tmp/cpu_samples.txt 2>/dev/null
  cat /sys/class/drm/card*/device/gpu_busy_percent >> /tmp/gpu_samples.txt 2>/dev/null
  sleep 5
done) &

(sleep 30; tmux send-keys -t a4 "Self-wake: PID=$GODOT_PID step=1/3. Check: ls -lh frames.raw" Enter) &
```

### 4. VAAPI encode (after Godot finishes)
```
timeout 120 ffmpeg -f rawvideo -pix_fmt rgba -s 608x1080 -framerate 25 \
  -i frames.raw -vf "format=nv12,hwupload" -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -y video_nosound.mp4
rm -f frames.raw
END_TS=$(date +%s)
```

### 5. Add audio
```
timeout 30 ffmpeg -i video_nosound.mp4 -i podcast_audio.mp3 \
  -c:v copy -c:a aac -shortest -y video.mp4
```

### 6. Log render metrics to render-log.csv
```
WALL_TIME=$((END_TS - START_TS))
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 video.mp4)
MB=$(stat --format=%s video.mp4 | awk '{printf "%.1f", $1/1024/1024}')
FRAMES=$(echo "$DUR * 25" | bc | cut -d. -f1)
RT=$(echo "scale=2; $DUR / $WALL_TIME" | bc)
CPU=$(awk '{sum+=$1; n++} END{printf "%.1f", sum/n}' /tmp/cpu_samples.txt 2>/dev/null || echo "0")
GPU=$(awk '{sum+=$1; n++} END{printf "%.1f", sum/n}' /tmp/gpu_samples.txt 2>/dev/null || echo "0")
echo "pipeline,wall_s,dur_s,rt_factor,mb,frames,cpu_avg,gpu_avg" > render-log.csv
echo "rawfile,$WALL_TIME,$DUR,$RT,$MB,$FRAMES,$CPU,$GPU" >> render-log.csv
touch done.txt
```

## Self-wake rule
Every `&` command is followed by `(sleep N; tmux send-keys -t a4 "context" Enter) &`.
Then continue working. Never wait synchronously.
