# ag-05 — Weston → Sway migration

## Model
`opencode-go/mimo-v2.5` (has vision)

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, self-wake pattern
- [../ag-04/AGENTS.md](../ag-04/AGENTS.md) — current desktop setup
- [../../e002-avatar-podcast/ag-09/wf-benchmark.md](../../e002-avatar-podcast/ag-09/wf-benchmark.md) — wf-recorder incompatibility findings

## Goal

Replace Weston with Sway (wlroots-based compositor) for:
- wf-recorder GPU-direct capture support
- Stable VNC access via wayvnc
- Full desktop (Waybar/wofi continue working)

## Context

- Weston currently running with `--backends=drm,vnc` (but VNC crashes on connect)
- wf-recorder incompatible with Weston (needs wlr-screencopy protocol)
- Sway 1.9 already installed
- Waybar, wofi installed and configured for Weston
- LD_PRELOAD UID fix in use for root DRM access
- System has no Xorg running (Wayland-only now)

## Task

### 1. Stop current Weston
Kill the running weston process (sudo kill). Verify port 5900 is free.

### 2. Configure Sway
Create `~/.config/sway/config` with:
- `output Virtual-1 resolution 1280x720` (for wf-recorder capture)
- Waybar as bar (same config from weston)
- Wofi as launcher
- Background color (so desktop is not empty)

### 3. Start Sway
```bash
sudo env XDG_RUNTIME_DIR=/run/user/1000 \
  LD_PRELOAD=/tmp/fakeuid.so \
  sway -d > /tmp/sway.log 2>&1 &
```

### 4. Install wayvnc
```bash
sudo apt-get install -y wayvnc
```

### 5. Start wayvnc against Sway
```bash
WAYLAND_DISPLAY=wayland-1 wayvnc :0 \
  --cert=/home/vuos/code/p4/e003-wayland-migration/ag-03/certs/cert.pem \
  --key=/home/vuos/code/p4/e003-wayland-migration/ag-03/certs/key.pem \
  -o 5900
```

### 6. Test wf-recorder with Sway
```bash
WAYLAND_DISPLAY=wayland-1 timeout 5 wf-recorder -f /tmp/sway-test.mp4 -c h264_vaapi
```

### 7. Verify VNC
Connect locally: `timeout 3 vncviewer localhost:5900`
Check the log for errors.

### 8. Fix waybar/wofi for Sway
Waybar config may need adjustments for Sway (different bar output config).
Ensure all launchers work (terminal, browser, editor, files).

### 9. Document
Write `sway-setup.md` with:
- Migration commands
- Sway config file
- WayVNC setup
- wf-recorder verification
- How to revert to Weston if needed

## Important rules
- ALL commands: `>/dev/null 2>&1 &` in background. Self-wake to continue.
- When using sudo in a separate window: close the window after use: `tmux kill-window -t <name>`
- Clean up all temporary windows (sudo, test, etc.) before finishing.

## Self-command
After reading, execute immediately.
