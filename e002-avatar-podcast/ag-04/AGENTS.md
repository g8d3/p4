# ag-04 — Video composer

## Inherits
- `../../e000-fundamentals/AGENTS.md` — principles, no /tmp, timeouts, GPU encoding
- `../AGENTS.md` — experiment scope

## Goal

Compose the final avatar podcast video with GPU-accelerated pipeline.

## Wait

This agent must wait for ag-03 to finish. Do NOT start until `../ag-03/done.txt` exists.

## Inputs

- `../ag-03/seg_*.mp3` — one audio file per dialogue line, in order
- `../ag-03/timing.json` — metadata for each segment
- `../ag-06/avatar_a.png` — persona A avatar
- `../ag-06/avatar_b.png` — persona B avatar
- `../ag-06/podcast_bg.png` — background
- `../ag-02/script.md` — script for subtitle text

## Task

### 1. Audio
Concatenate segment files in order:
```
ffmpeg -f concat -safe 0 -i <(for f in seg_*.mp3; do echo "file '$PWD/$f'"; done) -c copy podcast_audio.mp3
```

### 2. Render frames (Godot GPU)
Godot 4 is at `~/.local/bin/godot4`. Use Vulkan renderer:
```
godot4 --display-driver headless --script render_podcast.gd
```

### 3. Encode video (VAAPI GPU)
```
export LIBVA_DRIVER_NAME=radeonsi
ffmpeg -vaapi_device /dev/dri/renderD128 -framerate 25 -i frames/frame_%05d.png -i podcast_audio.mp3 -vf "format=nv12,hwupload" -c:v h264_vaapi -c:a aac -shortest video.mp4
```

### 4. Format
**9:16 vertical** (608x1080), NOT 16:9 landscape. Previous version failed with 1920x1080.

### 5. Subtitles
TikTok-style: short phrase chunks (2-4 words per subtitle), not full sentences. Alternating colors: #FFFFFF, #FFD700, #00FF88, #FF6B6B, #6BCBFF. Bottom position (Alignment=2, MarginV=50). Match the audio segment timing.

### Output

- `video.mp4` — final podcast with GPU-rendered avatars

### Completion

When finished, create `done.txt`:

```
touch done.txt
```

This triggers ag-05 via inotifywait.
