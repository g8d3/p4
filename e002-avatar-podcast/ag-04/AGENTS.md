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

### 1. Modify `render_podcast.gd`
Change the completion condition from time-based to frame-count-based:

```gdscript
# Replace: if elapsed >= duration:
# With:
var target_frames = int(duration * fps)
if frame_count >= target_frames:
    get_tree().quit()
```

This ensures `--write-movie` captures all frames correctly.

### 2. Render video with Godot `--write-movie`
No Weston or display server needed. Godot writes video directly:
```
DISPLAY=:0 timeout 600 ~/.local/bin/godot4 \
  --fixed-fps 25 \
  --rendering-driver vulkan \
  --write-movie video_raw.avi \
  --path godot_project \
  -- config.json
```

### 3. Convert AVI to H.264 MP4
```
timeout 30 ffmpeg -i video_raw.avi \
  -c:v libx264 -pix_fmt yuv420p \
  -y video_nosound.mp4
```

### 4. Add audio
```
timeout 30 ffmpeg -i video_nosound.mp4 -i podcast_audio.mp3 \
  -c:v copy -c:a aac -shortest \
  -y video.mp4
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
