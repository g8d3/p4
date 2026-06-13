# ag-07 — GPU pipeline engineer

## Inherits
- `../../e000-fundamentals/AGENTS.md` — principles, no /tmp, timeouts, GPU encoding, verification
- `../AGENTS.md` — experiment scope
- `../ag-04/AGENTS.md` — current video pipeline spec

## Goal

Research, test, and fix the full GPU video pipeline: Godot (Vulkan) + Xvfb + ffmpeg VAAPI capture. No CPU rendering or encoding.

## Task

The current ag-04 pipeline uses `--display-driver headless` which falls back to the Dummy renderer (CPU). The correct pipeline is:

1. **Xvfb** — virtual display (no physical screen needed)
2. **Godot** — render with Vulkan (`--rendering-driver vulkan --display-driver x11`) to the virtual display
3. **ffmpeg** — capture the virtual display with `h264_vaapi` (GPU encode)

### Issues to solve

1. `amdgpu_device_initialize failed` — check permissions (`groups`, `/dev/dri/renderD128`). May need `usermod -a -G render`.
2. Godot with `--display-driver headless` uses Dummy/CPU. Must use `--display-driver x11` with Xvfb.
3. ffmpeg x11grab must use `-vf "format=nv12,hwupload"` before `-c:v h264_vaapi`.

### Method

1. Test each component individually, then combine.
2. Use the sudo window (`sudo-vaapi` if still open, or open a new one) for any `usermod` or `apt` commands.
3. Write findings to `pipeline.md` with working commands.

### Output

- `pipeline.md` — working full-GPU pipeline commands
- Must be complete enough that ag-04 can copy-paste the pipeline

### Rules

- Verify everything with multiple tmux pane captures (do not assume from one capture).
- If a component fails, document the error and try the next approach.
