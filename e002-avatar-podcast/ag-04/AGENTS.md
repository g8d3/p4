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
rm -f video_raw.avi video_nosound.mp4 video.mp4 done.txt render-log.csv
export LIBVA_DRIVER_NAME=radeonsi
```

### 2. Start timer
```
START_TS=$(date +%s)
```

### 3. Godot `--write-movie` (no display needed, lightweight MJPEG)
```
timeout 600 ~/.local/bin/godot4 --fixed-fps 25 --rendering-driver vulkan \
  --display-driver headless --write-movie video_raw.avi \
  --path godot_project -- config.json &
GODOT_PID=$!

(sleep 30; tmux send-keys -t a4 "Self-wake: PID=$GODOT_PID step=1/3. Check: ls -lh video_raw.avi" Enter) &
```

### 4. VAAPI re-encode (GPU, converts MJPEG AVI → H.264 MP4)
```
timeout 120 ffmpeg -vaapi_device /dev/dri/renderD128 \
  -hwaccel vaapi -hwaccel_output_format vaapi \
  -i video_raw.avi \
  -c:v h264_vaapi -b:v 2M -y video_nosound.mp4
rm -f video_raw.avi
END_TS=$(date +%s)
```

### 5. Add audio
```
timeout 30 ffmpeg -i video_nosound.mp4 -i podcast_audio.mp3 \
  -c:v copy -c:a aac -shortest -y video.mp4
```

### 6. Log metrics to render-log.csv
```
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 video.mp4)
MB=$(stat --format=%s video.mp4 | awk '{printf "%.1f", $1/1024/1024}')
FRAMES=$(echo "$DUR * 25" | bc | cut -d. -f1)
WALL=$((END_TS - START_TS))
RT=$(echo "scale=2; $DUR / $WALL" | bc)
echo "pipeline,wall_s,dur_s,rt_factor,mb,frames" > render-log.csv
echo "writemovie,$WALL,$DUR,$RT,$MB,$FRAMES" >> render-log.csv
touch done.txt
```

## Self-wake rule
Every `&` command is followed by `(sleep N; tmux send-keys -t a4 "context" Enter) &`.
Then continue working. Never wait synchronously.
