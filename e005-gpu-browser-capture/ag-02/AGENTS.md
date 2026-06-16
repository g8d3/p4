# ag-02 — Dynamic browsing screencast

## Model
`opencode-go/mimo-v2.5` (has vision for self-review)

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, self-wake, background commands
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Prerequisite

Sway runs permanently as a systemd service. **Do not start or stop Sway.** It's always available.

```bash
export XDG_RUNTIME_DIR=/run/sway-recording
export WAYLAND_DISPLAY=wayland-1
export DISPLAY=:0
```

## Goal

Record a **20-second video** of yourself browsing the web. Vertical 9:16 format. The video must show real browser content — not blank screen, not static.

You decide what to browse. You narrate via the terminal. You verify the result and retry if needed.

## Recording pipeline (GPU only, zero CPU)

```bash
# 1. Record full screen with DMA-BUF (GPU direct, 0 CPU)
wf-recorder -f raw.mp4 -c h264_vaapi -b 4M &
REC_PID=$!

# 2. Browse (see below)

# 3. Stop
kill $REC_PID

# 4. Crop to vertical 9:16 with VAAPI (GPU, 0 CPU)
ffmpeg -i raw.mp4 -vf "crop=608:1080:0:0,format=nv12,hwupload" -c:v h264_vaapi capture.mp4
```

## Tools

| Tool | What for |
|------|----------|
| `ydotool type/text/key/click` | Simulate keyboard/mouse on Wayland (needs sudo) |
| `swaymsg [criteria] move position 0 0` | Position browser window in capture region |
| `swaymsg [criteria] resize set width 608 height 1080` | Resize browser to fill vertical frame |
| `swaymsg -t get_tree` | Inspect windows (titles, positions, focus) |
| `ffprobe` | Check video resolution, bitrate, duration |
| `ffmpeg -i in -vf "select=eq(n\,0)" -vframes 1 frame.png` | Extract frame for visual check |

## What to do

1. **Set env vars** (XDG_RUNTIME_DIR, WAYLAND_DISPLAY, DISPLAY)
2. **Open browser** (`epiphany` or `google-chrome`)
3. **Position it** at 0,0 with size 608×1080 using swaymsg
4. **Test** — record 2s, check file size (should be > 100 KB), extract frame, read with vision
5. **Record 20s** — wf-recorder in background, browse with ydotool, narrate with echo
6. **Crop** to 608×1080 with ffmpeg VAAPI
7. **Verify** — file ≥ 1 MB, resolution 608×1080, frame shows real content
8. **Self-review** with Mimo 2.5 vision → write review.md

If any verification fails, diagnose and retry. Don't proceed with a broken video.

## Common pitfalls

- **Browser not visible?** Use `swaymsg -t get_tree` to find its window, then `move position 0 0`
- **ydotool not working?** It needs sudo. Click browser first to focus: `sudo ydotool click 1`
- **Small video file?** The screen might be dark. Open bright pages (google.com, news, GitHub).
- **Wrong resolution?** Run `ffprobe raw.mp4`. If not 1920×1080, the monitor EDID may differ. Adjust crop accordingly.
