# Capture Fix — ag-07

## Why x11grab Failed

The ag-04 pipeline ran:
```
weston --backend=headless --renderer=gl --socket=wayland-99
ffmpeg -f x11grab -video_size 608x1080 -i :99.0 ...
```

**x11grab requires an X11 display** (e.g. `:0`, `:99.0`). Weston headless creates a **Wayland-only** compositor — the socket `wayland-99` is a Wayland IPC socket, not an X11 display. There is no X11 display `:99.0` to capture, so ffmpeg fails immediately.

## Tested Approaches

### Option 1: Godot `--write-movie` (RECOMMENDED)

Godot has a built-in movie writer that captures rendered frames directly to a video file. No display server or capture tool needed.

**Command:**
```bash
DISPLAY=:0 godot4 \
  --fixed-fps 25 \
  --rendering-driver vulkan \
  --write-movie output.avi \
  --path godot_project \
  -- config.json
```

**Results:**
- Output: 608x1080 MJPEG AVI @ 25fps
- Wall time: 2.56s for 2s video (50% real-time speed)
- CPU render time: 0.06 ms/frame avg
- GPU render time: 0.30 ms/frame avg
- Encoding time: 6.26 ms/frame avg
- Max RSS: 229 MB
- Verified: ffprobe confirms valid 25fps h264 output after conversion

**Notes:**
- `DISPLAY=:0` is required even though Godot renders internally (X11 display server initialization needed)
- `--fixed-fps 25` is forced by `--write-movie` and sets the output FPS
- `--disable-vsync` can speed up rendering
- Output is MJPEG/AVI — convert to H.264 MP4 with: `ffmpeg -i output.avi -c:v libx264 -pix_fmt yuv420p output.mp4`
- The `--write-movie` mode skips `save_png()` calls in the script

**Required script change:** The current `render_podcast.gd` uses `Time.get_ticks_msec()` for elapsed time. In `--write-movie` mode, Godot runs at the fixed FPS rate. The duration check `elapsed >= duration` should work, but the frame count may be lower than expected (22 vs 50 for 2s at 25fps). Consider frame-count-based duration instead:
```gdscript
var target_frames = int(duration * fps)
if frame_count >= target_frames:
    get_tree().quit()
```

### Option 2: Weston `--backend=x11` + x11grab

Weston runs as an X11 window inside the real X11 display (`:0`), making it visible to x11grab.

**Command:**
```bash
# Start Weston as X11 window
DISPLAY=:0 weston --backend=x11 --socket=wayland-x11test --width=608 --height=1080 &

# Start ffmpeg capture
ffmpeg -f x11grab -video_size 1024x600 -framerate 25 -i :0.0+offset_x,offset_y \
  -vf "format=nv12,hwupload" -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -y output.mp4 &

# Start Godot on Wayland
WAYLAND_DISPLAY=wayland-x11test godot4 --display-driver wayland --rendering-driver vulkan \
  --path godot_project -- config.json
```

**Results:**
- x11grab capture works (verified with 3s test)
- Window appears at 1024x600 (default) or custom size with `--width`/`--height`
- Captures the X11 root display including the Weston window

**Problems:**
- Complex 3-process pipeline (Weston + ffmpeg + Godot)
- Window position is non-deterministic (needs xwininfo to find offset)
- Resolution is fixed to Weston window size (not the 608x1080 target)
- Cannot use GPU acceleration for capture without VAAPI setup on the X11 path

### Option 3: wf-recorder / pipewire

**Not available.** `wf-recorder` is not installed. `pipewire` is installed but there is no screen capture tool using it.

## Recommendation

**Use Option 1: Godot `--write-movie`.** It is:
- Simpler (single process, no Weston needed)
- Faster (GPU-accelerated rendering + encoding)
- More reliable (no display server coordination)
- The built-in Godot movie writer is designed for this exact use case

### Updated Pipeline (ag-04)

Replace the Weston + x11grab pipeline with:

```bash
# Step 1: Render video with Godot (no Weston needed)
DISPLAY=:0 timeout 600 godot4 \
  --fixed-fps 25 \
  --rendering-driver vulkan \
  --write-movie video_raw.avi \
  --path godot_project \
  -- config.json

# Step 2: Convert to H.264 MP4
timeout 30 ffmpeg -i video_raw.avi \
  -c:v libx264 -pix_fmt yuv420p \
  -y video_nosound.mp4

# Step 3: Add audio
timeout 30 ffmpeg -i video_nosound.mp4 -i podcast_audio.mp3 \
  -c:v copy -c:a aac -shortest \
  -y video.mp4
```

Weston headless is no longer needed for the render pipeline.
