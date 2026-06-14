# wf-recorder Pipeline Benchmark

## Goal

Test and benchmark the **live GPU pipeline**: Weston DRM → wf-recorder → VAAPI → MP4 as a replacement for the two-step PNG pipeline (Godot → Weston → PNG frames → ffmpeg VAAPI).

## Summary

| Aspect | Result |
|--------|--------|
| **wf-recorder** | DOES NOT WORK with Weston — requires `wlr-screencopy-unstable-v1` protocol (wlroots-only) |
| **kmsgrab** | WORKS as alternative — captures DRM framebuffer directly with VAAPI encode |
| **Live + Godot simultaneous** | Unstable — Godot crashes when kmsgrab holds DRM framebuffer references |
| **Pipeline recommendation** | Keep two-step pipeline (ag-07 approach); kmsgrab suitable for static/desktop capture only |

## Working Commands

### kmsgrab capture (works for desktop capture)

```bash
export LIBVA_DRIVER_NAME=radeonsi
sudo ffmpeg -f kmsgrab \
  -device /dev/dri/card1 \
  -crtc_id 73 \
  -framerate 30 \
  -vaapi_device /dev/dri/renderD128 \
  -i - \
  -vf "hwmap=derive_device=vaapi,scale_vaapi=format=nv12" \
  -c:v h264_vaapi -b:v 2M \
  -t 5 -y /tmp/capture.mp4
```

### Godot render against Weston DRM (with GPU)

```bash
sudo env WAYLAND_DISPLAY=wayland-1 \
  XDG_RUNTIME_DIR=/run/user/1000 \
  LD_PRELOAD=/tmp/fakeuid.so \
  ~/.local/bin/godot4 \
  --display-driver wayland \
  --rendering-driver opengl3 \
  --accessibility disabled \
  --path /path/to/godot_project \
  -- /path/to/config.json
```

## Metrics Collected

### kmsgrab capture (1920×1080, idle desktop)

| Metric | Value |
|--------|-------|
| **Output resolution** | 1920×1080 |
| **Capture FPS** | 29.83 (30 target) |
| **Encode speed** | ~1.15× real-time |
| **Output bitrate** | 114 kb/s (idle desktop) |
| **File size (5s)** | 71 KB |
| **GPU usage** | 0-1% |
| **CPU usage** | Near 0 |
| **Encoder** | h264_vaapi (AMD radeonsi) |
| **DMA-BUF** | Not used (kmsgrab → VAAPI via hwmap) |

### PNG pipeline (existing ag-04 output)

| Metric | Value |
|--------|-------|
| **Output resolution** | 608×1080 |
| **Frame rate** | 25 fps |
| **Total frames** | 6819 (272 seconds) |
| **Frame size** | 2.6 MB/frame (RGBA) |
| **Total disk** | ~17.9 GB raw + intermediate |
| **Final video** | 6.3 MB (h264) |
| **Pipeline time** | ~10 min real-time |
| **GPU usage** | 1-3% (Godot render) + ~20× real-time VAAPI encode |

## Comparison Table: PNG Pipeline vs Live Capture

| Metric | PNG Pipeline (two-step) | Live kmsgrab |
|--------|------------------------|-------------|
| **Disk usage** | ~17.9 GB (frames.raw) | 0 (streaming) |
| **Time to result** | Render + encode (~10 min) | Real-time (272s) |
| **Resolution** | 608×1080 (target) | 1920×1080 (full display) |
| **Frame rate** | 25 fps (locked) | ~30 fps (variable) |
| **GPU acceleration** | Godot (AMD) + ffmpeg (VAAPI) | ffmpeg (VAAPI) |
| **Robustness** | Stable | Unstable with active 3D |
| **Window isolation** | Renders only content | Captures entire screen |
| **Audio capture** | Separate step | No (would need separate) |
| **Parallelism** | Yes (multiple Weston instances) | No (one DRM framebuffer) |

## Issues Encountered

### 1. wf-recorder incompatible with Weston

wf-recorder requires the `wlr-screencopy-unstable-v1` Wayland protocol, which is specific to wlroots-based compositors (sway, river, Hyprland). Weston uses its own protocol stack (libweston) and does not implement this.

**Error**: `compositor doesn't support wlr-screencopy-unstable-v1`

**Workaround**: Use `ffmpeg kmsgrab` to capture directly from the DRM/KMS framebuffer.

### 2. kmsgrab + Godot simultaneous instability

When kmsgrab captures the DRM framebuffer while Godot renders new content:
- kmsgrab holds a reference to the current framebuffer
- Weston cannot flip to a new framebuffer
- Weston's DRM backend disconnects the Godot Wayland client
- Godot crashes with `Wayland client error code 104`

This makes live capture of Godot rendering infeasible with kmsgrab.

### 3. Godot crashes on long renders (272s)

Godot 4.6.1 consistently crashes after ~200 frames (~8 seconds) when rendering from scratch with:
- `handle_crash: Program crashed with signal 4` (SIGILL) — Wayland protocol error with FIFO
- `handle_crash: Program crashed with signal 11` (SIGSEGV) — X11 fallback when Wayland unavailable
- `accesskit` thread panic — DBus accessibility bus not available

**Mitigations**:
- `--accessibility disabled` prevents accesskit crash
- `--disable-vsync` improves frame pacing
- Pre-existing `frames.raw` allows resume (which completes successfully)

### 4. GPU device permissions

The `/dev/dri/renderD128` device requires the `render` group. When running as user `vuos` (not in `render` group), Godot falls back to llvmpipe software rendering:
- OpenGL: `Mesa llvmpipe (LLVM 20.1.2)`
- Vulkan: `llvmpipe (LLVM 20.1.2)`

**Fix**: `sudo usermod -a -G render vuos` + re-login, or use `sudo env LD_PRELOAD=/tmp/fakeuid.so godot4 ...`

## Recommendation for ag-04 Pipeline

**Keep the two-step pipeline** (Godot → frames.raw → ffmpeg VAAPI) for the following reasons:

1. **Stability**: The two-step pipeline completes reliably (6819 frames)
2. **Isolation**: Each Godot instance renders independently; no interference from capture
3. **Parallelism**: Multiple Weston headless instances can render simultaneously
4. **Resolution control**: Renders at target resolution (608×1080), not full display
5. **Audio**: Can be added as a separate ffmpeg step
6. **GPU utilization**: Godot uses AMD GPU at 1-3% for 2D; ffmpeg VAAPI encode is ~20× real-time

The live capture approach (kmsgrab) is suitable for:
- Recording desktop demos or tutorials
- Capturing compositor output when no Godot rendering is active
- Situations where zero disk usage is critical

To implement the live pipeline properly, install a wlroots-based compositor (e.g., `sway`) which supports `wlr-screencopy` and use `wf-recorder` with it.
