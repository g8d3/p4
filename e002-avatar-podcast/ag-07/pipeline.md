# GPU Video Pipeline — Working Commands

## Prerequisites

1. **User in render group** (one-time fix):
   ```bash
   sudo usermod -a -G render $(whoami)
   ```
   Then log out and back in, or run `newgrp render` in a new shell.

2. **Verify VAAPI works**:
   ```bash
   export LIBVA_DRIVER_NAME=radeonsi
   vainfo 2>&1 | grep -i h264
   ```
   Should show `VAProfileH264Main: VAEntrypointEncSlice`.

## Pipeline A: Two-Step (Recommended)

Most reliable. Godot renders frames to PNG, then ffmpeg encodes with VAAPI.

### Step 1: Godot render frames

```bash
cd /home/vuos/code/p4/e002-avatar-podcast/ag-04/godot_project

# Create output directory
mkdir -p frames

# Render with Vulkan on Xvfb
# IMPORTANT: Use --display-driver x11, NOT --headless
# --headless forces Dummy/CPU renderer even with --rendering-driver vulkan
xvfb-run --auto-servernum --server-args="-screen 0 608x1080x24" \
  ~/.local/bin/godot4 \
  --rendering-driver vulkan \
  --display-driver x11 \
  -- /path/to/config.json
```

**Key flags**:
- `--rendering-driver vulkan` — use Vulkan, not OpenGL
- `--display-driver x11` — render to X11 display (Xvfb), NOT `--headless`
- `--` separates Godot args from script args
- Script receives config path via `OS.get_cmdline_user_args()`

**Config JSON format** (see `config.json` for full example):
```json
{
  "segments": [{"start": 0.0, "end": 2.304, "speaker": "A", "text": "..."}],
  "duration": 272.784,
  "fps": 25,
  "w": 608,
  "h": 1080,
  "output_dir": "/path/to/frames",
  "bg": "/path/to/podcast_bg.png",
  "avatar_a": "/path/to/avatar_a.png",
  "avatar_b": "/path/to/avatar_b.png"
}
```

### Step 2: ffmpeg VAAPI encode

```bash
export LIBVA_DRIVER_NAME=radeonsi

# Without audio (just video)
ffmpeg -vaapi_device /dev/dri/renderD128 \
  -framerate 25 \
  -i frames/frame_%05d.png \
  -vf "format=nv12,hwupload" \
  -c:v h264_vaapi \
  -y output.mp4

# With audio
ffmpeg -vaapi_device /dev/dri/renderD128 \
  -framerate 25 \
  -i frames/frame_%05d.png \
  -i podcast_audio.mp3 \
  -vf "format=nv12,hwupload" \
  -c:v h264_vaapi \
  -c:a aac \
  -shortest \
  -y output.mp4
```

**Key flags**:
- `-vaapi_device /dev/dri/renderD128` — VAAPI device
- `-vf "format=nv12,hwupload"` — REQUIRED before VAAPI encoder
- `-c:v h264_vaapi` — GPU-accelerated H.264 encoding
- `-shortest` — stop at shortest stream (video or audio)

### Step 3: Concatenate audio (if segments)

```bash
# Create file list
ls seg_*.mp3 | sort | while read f; do echo "file '$PWD/$f'"; done > audio_list.txt

# Concat
ffmpeg -f concat -safe 0 -i audio_list.txt -c copy podcast_audio.mp3
```

## Pipeline B: Real-Time x11grab

Captures directly from Xvfb while Godot renders. Faster (1x speed) but no audio in capture.

```bash
cd /home/vuos/code/p4/e002-avatar-podcast/ag-04/godot_project

xvfb-run --auto-servernum --server-args="-screen 0 608x1080x24" bash -c "
  # Start Godot rendering to the virtual display
  DISPLAY=\$DISPLAY ~/.local/bin/godot4 \
    --rendering-driver vulkan \
    --display-driver x11 \
    -- /path/to/config.json &
  GODOT_PID=\$!

  sleep 1

  # Capture from the display with VAAPI
  export LIBVA_DRIVER_NAME=radeonsi
  timeout <duration+5> ffmpeg \
    -f x11grab -video_size 608x1080 -framerate 25 -i \$DISPLAY.0 \
    -t <duration> \
    -vf \"format=nv12,hwupload\" \
    -vaapi_device /dev/dri/renderD128 \
    -c:v h264_vaapi \
    -y output.mp4

  wait \$GODOT_PID 2>/dev/null
"
```

Then add audio separately:
```bash
ffmpeg -i output.mp4 -i podcast_audio.mp3 -c:v copy -c:a aac -shortest final.mp4
```

## Performance

| Component | Speed | Notes |
|-----------|-------|-------|
| Godot Vulkan render | ~13 fps | On Xvfb with llvmpipe (no DRI3) |
| ffmpeg VAAPI encode | ~15x real-time | 608x1080 H.264 |
| Full pipeline (2-step) | ~2x real-time | 10s video in ~20s |
| Full pipeline (x11grab) | 1x real-time | 10s video in ~10s |

## Troubleshooting

### `amdgpu_device_initialize failed`
- User not in `render` group. Run: `sudo usermod -a -G render $(whoami)`
- Then `newgrp render` or log out/in.

### `--headless` renders black/empty frames
- `--headless` forces Dummy renderer (CPU). Use `--display-driver x11` with Xvfb instead.

### `vulkan: No DRI3 support detected`
- Non-fatal. Xvfb falls back to llvmpipe (software). Rendering still works.
- For true GPU rendering, use a real X server with DRI3.

### `Parameter "t" is null` in capture_frame
- Caused by Dummy renderer (headless). Fix: use `--display-driver x11`.

### ffmpeg `No quality level set; using default (20)`
- Normal warning. VAAPI uses default quality. Add `-qp 18` for higher quality.

## Verified Working Commands

```bash
# Quick test (2 seconds, 50 frames)
cat > /tmp/quick_config.json << 'EOF'
{
  "segments": [{"start": 0.0, "end": 1.0, "speaker": "A", "text": "Hi"}, {"start": 1.0, "end": 2.0, "speaker": "B", "text": "Hello"}],
  "duration": 2.0, "fps": 25, "w": 608, "h": 1080,
  "output_dir": "/tmp/frames",
  "bg": "/home/vuos/code/p4/e002-avatar-podcast/ag-06/podcast_bg.png",
  "avatar_a": "/home/vuos/code/p4/e002-avatar-podcast/ag-06/avatar_a.png",
  "avatar_b": "/home/vuos/code/p4/e002-avatar-podcast/ag-06/avatar_b.png"
}
EOF

mkdir -p /tmp/frames

# Render
xvfb-run --auto-servernum --server-args="-screen 0 608x1080x24" \
  ~/.local/bin/godot4 --rendering-driver vulkan --display-driver x11 \
  -- /tmp/quick_config.json

# Encode
export LIBVA_DRIVER_NAME=radeonsi
ffmpeg -vaapi_device /dev/dri/renderD128 -framerate 25 \
  -i /tmp/frames/frame_%05d.png \
  -vf "format=nv12,hwupload" -c:v h264_vaapi -y /tmp/quick_output.mp4

# Verify
ffprobe /tmp/quick_output.mp4
```
