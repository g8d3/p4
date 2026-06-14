# ag-09 — wf-recorder pipeline benchmark

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, self-wake pattern
- [../ag-07/pipeline-v2.md](../ag-07/pipeline-v2.md) — previous GPU pipeline research

## Goal

Test and benchmark the **live GPU pipeline**: Weston DRM → wf-recorder → VAAPI → MP4, as a replacement for the two-step PNG pipeline.

## Context

- Weston is **already running** with `--backends=drm,vnc` on socket `wayland-1`
- The system is GPU-only (no Xorg, no lightdm)
- Previous pipeline (ag-07): Godot → Weston headless → PNG frames → ffmpeg VAAPI (two steps, writes frames to disk)
- New pipeline: Godot → running Weston DRM → wf-recorder capture → VAAPI encode (live, zero disk)
- wf-recorder is installed (v0.4.1)
- Weston runs as root with LD_PRELOAD for the UID fix

## Task

### 1. Test wf-recorder capture from running Weston

```bash
# First, check available Wayland sockets
ls /run/user/1000/wayland-*

# Test live capture (5 seconds)
WAYLAND_DISPLAY=wayland-1 timeout 8 wf-recorder -f /tmp/wf_test.mp4 -c h264_vaapi -b 2M
```

If this fails, try with `--no-dmabuf` flag or different pixel formats.

### 2. Benchmark metrics

Record these metrics for each test:

| Metric | How to measure |
|---|---|
| **Output FPS** | `ffprobe /tmp/wf_test.mp4 2>&1 \| grep fps` |
| **GPU usage** | `cat /sys/class/drm/card*/device/gpu_busy_percent` (before/after) |
| **CPU usage** | `top -bn1 \| grep "wf-recorder\|ffmpeg"` |
| **File size** | `ls -lh /tmp/wf_test.mp4` |
| **Encode time** | How long the capture took |
| **Real-time factor** | Capture duration / wall clock time |
| **DMA-BUF** | Check if wf-recorder used GPU-direct (`wf-recorder --verbose`) |

### 3. Compare with PNG pipeline

Run a Godot test render against the running Weston to measure:
```bash
WAYLAND_DISPLAY=wayland-1 \
  ~/.local/bin/godot4 \
  --display-driver wayland \
  --rendering-driver vulkan \
  --path /home/vuos/code/p4/e002-avatar-podcast/ag-04/godot_project \
  -- /home/vuos/code/p4/e002-avatar-podcast/ag-04/godot_project/config.json
```

### 4. Test capture with Godot rendering (simultaneous)

Start Godot rendering, then simultaneously capture with wf-recorder. Measure:
- Does capture FPS match Godot render FPS?
- Are frames dropped?
- Is there a performance hit on the compositor?

### 5. Document

Write `wf-benchmark.md` with:
- Working commands
- All metrics collected
- Comparison table: PNG pipeline vs live capture
- Recommendation for ag-04 pipeline
- Any issues encountered

## Self-command
After reading, execute immediately. ALL commands: `>/dev/null 2>&1 &`. Self-wake to continue.
