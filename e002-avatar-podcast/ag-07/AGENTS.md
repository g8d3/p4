# ag-07 — GPU pipeline engineer (v2)

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, pkill rule
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Command execution
All commands need `timeout <seconds>`. Examples:
- `timeout 30 weston --backend=headless ...` — Weston startup
- `timeout 60 sudo Xorg :1 -config ...` — Xorg test
- `timeout 30 xdpyinfo, vainfo, ls` — quick checks

## Goal

Make Godot render with real GPU (not CPU/llvmpipe) in a headless/automated setup.

## Context

- **Option A** (real display `:0`): works with GPU. Not the focus here.
- **Option B** (virtual X server with DRI3): needs research and testing. Xvfb falls back to llvmpipe (CPU) because it has no DRI3 support.

## Task

Research and test Option B: a virtual X server with DRI3 that allows Vulkan hardware acceleration.

### Approaches to test

1. **Xorg with dummy/modesetting driver**: Start a second X server with the AMD GPU driver on a virtual display (e.g., `:1`). Requires configuring an xorg.conf with the amdgpu driver.
   ```
   sudo Xorg :1 -configure
   # Then start with the config
   sudo Xorg :1 -config ~/xorg.conf.virtual
   ```

2. **Xephyr**: Nested X server that supports DRI3. Runs inside the existing X server but provides its own display with GPU access.
   ```
   Xephyr :1 -screen 608x1080 -dri3
   ```

3. **Weston/Wayland**: Wayland compositor with DRM backend that could provide a headless GPU-accelerated display.

### Output

Write `pipeline-v2.md` with:
- Which approaches work and which don't
- Exact working commands for each working approach
- GPU verification: confirm GPU busy > 0% during render
- Recommendation

### Rules

- Use the sudo window for any privileged commands.
- All commands need `timeout`.
- Never use `pkill` broadly — use `kill $PID`.
- Verify with multiple captures (don't assume from one).
