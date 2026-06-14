# e003 — Wayland migration

**Goal**: Configure the system to run Weston as a Wayland compositor session alongside the existing Xorg session. This enables GPU-direct video capture with wf-recorder.

## Context

Current system runs Xorg. Weston/wf-recorder requires Wayland. We need to install Weston and configure it as a selectable session at login.

## What needs to happen

1. Install weston (already installed) with XWayland support
2. Create a Weston session file: `/usr/share/wayland-sessions/weston.desktop` (or verify it exists)
3. Test launching Weston from the display manager (login screen)
4. Once in a Weston session, verify: `wf-recorder -f test.mp4 -c h264_vaapi` works
5. Document the process

## Agent

- **ag-01**: research and execute the migration. Read e000-fundamentals for principles.
