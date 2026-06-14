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

### 2. Render with Godot (background + self-wake)
```
timeout 600 ~/.local/bin/godot4 --rendering-driver vulkan --display-driver headless \
  --path godot_project -- config.json &
GODOT_PID=$!
(sleep 30; tmux send-keys -t a4 "Self-wake: PID=$GODOT_PID step=1/3. Check: ls -lh frames.raw" Enter) &
```

### 3. VAAPI encode (after Godot finishes)
```
timeout 120 ffmpeg -f rawvideo -pix_fmt rgba -s 608x1080 -framerate 25 \
  -i frames.raw -vf "format=nv12,hwupload" -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -y video_nosound.mp4
rm -f frames.raw
```

### 4. Add audio
```
timeout 30 ffmpeg -i video_nosound.mp4 -i podcast_audio.mp3 \
  -c:v copy -c:a aac -shortest -y video.mp4
touch done.txt
```

## Self-wake rule
Every `&` command is followed by `(sleep N; tmux send-keys -t a4 "context" Enter) &`.
Then continue working. Never wait synchronously.
