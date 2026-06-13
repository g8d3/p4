# ag-07 — GPU pipeline engineer (v3)

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../ag-04/AGENTS.md](../ag-04/AGENTS.md) — current pipeline spec

## Command execution
All commands need `timeout <seconds>`.

## Goal

Find why x11grab capture fails on Weston headless and determine the correct capture method.

## Problem

ag-04 attempted:
```
weston --backend=headless --renderer=gl --socket=wayland-99
ffmpeg -f x11grab -video_size 608x1080 -i :99.0 ...
```
ffmpeg x11grab failed because Weston headless is Wayland-only — there is no X11 display `:99.0` to capture.

## Task

Research and recommend the best capture method. Options to investigate:

1. **Godot `--write-movie output.avi`** — built-in movie writer. Check if it works with `--display-driver wayland --rendering-driver vulkan`. Test with a short render.

2. **Weston `--backend=x11`** — Weston runs as an X11 window inside the real display `:0`. This creates both a Wayland socket (for Godot) and a visible X11 window (for x11grab). Test if x11grab can capture it.

3. **Weston with pipewire/wf-recorder** — not installed, would need sudo install.

### Test each option

- Write a short test (2-second render) for each working option
- Measure: GPU usage, CPU usage, frames captured, speed
- Verify the output video plays correctly

### Output

Write `capture-fix.md` with:
- Why x11grab failed (explanation)
- Tested approaches and results
- Exact working commands for the best approach
- Update the ag-04 pipeline with the fix if needed
