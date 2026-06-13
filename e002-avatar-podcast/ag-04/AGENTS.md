# ag-04 — Video composer

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, GPU encoding
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../ag-07/pipeline-v2.md](../ag-07/pipeline-v2.md) — Weston GPU pipeline

## Command execution
All commands need `timeout <seconds>`. Examples:
- `timeout 10 ls, cat, grep` — quick checks
- `timeout 30 sudo apt install -y weston` — install
- `timeout 600 weston ...` — Weston server
- `timeout 600 godot4 ...` — Godot rendering
- `timeout 600 ffmpeg ...` — capture + encode

## Goal

Compose the final avatar podcast video with a pure GPU pipeline: Godot renders to a Weston display, ffmpeg captures it live with VAAPI. No intermediate PNG files.

## Wait

Do NOT start until `../ag-03/done.txt` exists.

## Inputs

- `../ag-03/seg_*.mp3` — one audio file per dialogue line, in order
- `../ag-03/timing.json` — metadata for each segment
- `../ag-06/avatar_a.png` — persona A avatar
- `../ag-06/avatar_b.png` — persona B avatar
- `../ag-06/podcast_bg.png` — background
- `../ag-02/script.md` — script for subtitle text
- `godot_project/render_podcast.gd` — needs modification

## Pipeline (GPU only, no PNGs)

### 1. Install weston if missing
```
timeout 30 sudo apt install -y weston
```

### 2. Modify `render_podcast.gd`
The current version saves every frame as PNG to disk. **Remove all `save_png` calls.** Instead:
- Use a timer to render frames at 25fps, synchronized to segment timing
- Each frame renders the scene (avatars, background, speaker highlight)
- Draw subtitles directly in the scene using Godot's `Label` node (not as separate SRT)
- Wait for real-time elapsed between frames (or as close as possible)
- The display output IS the video — ffmpeg captures it

### 3. Start capture pipeline
```
# Start Weston (virtual display) ← timeout 15 for startup
timeout 15 weston --backend=headless --renderer=gl --socket=wayland-99 &
sleep 2

# Start ffmpeg capture (GPU → GPU, no intermediate files) ← timeout matches video duration
export LIBVA_DRIVER_NAME=radeonsi
WAYLAND_DISPLAY=wayland-99 \
  timeout 600 ffmpeg -f x11grab -video_size 608x1080 -framerate 25 -i :99.0 \
  -vf "format=nv12,hwupload" -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -y video_nosound.mp4 &
FFPID=$!

# Run Godot (renders to Weston display, captured by ffmpeg) ← timeout matches video
WAYLAND_DISPLAY=wayland-99 \
  timeout 600 ~/.local/bin/godot4 \
  --display-driver wayland \
  --rendering-driver vulkan \
  --path godot_project \
  -- config.json

# Stop capture when Godot exits
kill $FFPID 2>/dev/null; wait $FFPID 2>/dev/null
```

### 4. Add audio ← timeout 30 for encoding
```
export LIBVA_DRIVER_NAME=radeonsi
timeout 30 ffmpeg -i video_nosound.mp4 -i podcast_audio.mp3 -c:v copy -c:a aac -shortest -y video.mp4
```

### 5. Add subtitles (if not rendered in Godot)
Use SRT with strict formatting rules (see Subtitles section).

## Format
**9:16 vertical** (608x1080).

## Subtitles

### Splitting rules (by word count + timing)

| Words in sentence | Max chunks | Max words per chunk |
|---|---|---|
| 1-4 | 1 | 4 |
| 5-10 | 2 | 5 |
| 11-15 | 3 | 5 |
| 16-20 | 4 | 5 |
| 21+ | 5 | 5 |

Split at natural boundaries (commas, periods, conjunctions). Never break a phrase across chunks.

### Minimum display time
Each subtitle must stay on screen for at least 1.2 seconds. If a chunk's audio is shorter, extend its display to 1.2s.

### Maximum display time
If a chunk would stay on screen longer than 3 seconds, split it further.

### Style
- Alternating colors: #FFFFFF, #FFD700, #00FF88, #FF6B6B, #6BCBFF
- Font size: at least 18px (readable on mobile)
- Bottom position (Alignment=2, MarginV=60)
- Font: Monospace

## Output
- `video.mp4` — final podcast, GPU-rendered, no PNGs

## Completion
When finished, create `done.txt` to trigger ag-05 review.
