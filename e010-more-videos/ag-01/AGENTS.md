# ag-01 — Virtual display + recording pipeline

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Model
`opencode-go/mimo-v2.5` (has vision for self-review)

## Goal
Record a screencast of a terminal doing something interesting (typing commands, editing code, browsing files). Must be an actual screen recording via Wayland, not a composited video. Include audio narration and subtitles.

## What to do

1. Set up a virtual display with Sway (Wayland) — 608x1080 vertical
2. Open a terminal window (foot) in the virtual display
3. Do something interesting: type commands, navigate files, edit code, run a script
4. Record the screen with `wf-recorder` or `ffmpeg` via `pipewire`/`wlroots` capture
5. Add subtitles (TikTok-style: short chunks, bottom position)
6. Add narration via edge-tts (Colombian voice: es-CO-SalomeNeural)
7. Output final video to `./output/`
8. Self-review: check resolution, content visibility, audio sync, subtitles

## Key commands

```bash
# Start Sway on the virtual display
SWAYSOCK= SWONLY=1 WLR_BACKENDS=headless sway -d 2> sway.log &

# Open terminal
WAYLAND_DISPLAY=wayland-1 foot --maximized &

# Record with wf-recorder (Wayland native)
WAYLAND_DISPLAY=wayland-1 wf-recorder -f raw_capture.mp4 -g 608x1080+0+0

# Or with ffmpeg via pipewire
WAYLAND_DISPLAY=wayland-1 ffmpeg -f pipewire -i 0 -c:v h264_vaapi output.mp4
```

## Self-review
Use your vision capability to examine frames. Check:
- Is the content visible and readable?
- Is the resolution correct (608x1080 vertical)?
- Are there black/blank frames?
- Are subtitles present and readable?
- Is there audio?

## Video metadata
Each video must include a `metadata.json` in `./output/` with:

```json
{
  "duration_sec": 120,
  "resolution": "608x1080",
  "display": "wayland-sway-headless",
  "capture_method": "wf-recorder",
  "encoding": "h264_vaapi",
  "audio": true,
  "subtitles": true,
  "cpu_usage_avg": 45.2,
  "ram_mb": 512,
  "gpu_usage_avg": 12.5,
  "narration": "es-CO-SalomeNeural",
  "narration_method": "edge-tts",
  "recording_start": "2026-06-23T10:00:00",
  "recording_end": "2026-06-23T10:02:00"
}
```

## Success criteria
- Video file exists and is > 5 MB
- Resolution is 608x1080 vertical
- Content is visible and readable
- Audio is present (narration + demo sounds)
- Subtitles are present
- No black/blank frames
- metadata.json is present
