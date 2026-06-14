# ag-01 — Weston/Wayland session setup

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, self-wake pattern

## Goal

Configure a Weston (Wayland) session on this system so that GPU-direct video capture with wf-recorder works.

## Task

### 1. Check current state
- Is weston installed? (`weston --version`)
- Is XWayland supported? (`apt list --installed | grep xwayland`)
- Is there a session file? (`ls /usr/share/wayland-sessions/`)

### 2. Install missing packages (sudo window)
- `xwayland` (if missing)
- `weston` (if missing)
- Verify `wf-recorder` is installed

### 3. Create or verify session file
Check if `/usr/share/wayland-sessions/weston.desktop` exists. If not, create it:
```
[Desktop Entry]
Name=Weston
Comment=Weston Wayland Compositor
Exec=weston
Type=Application
```

### 4. Test Weston session
- From the login screen (lightdm/gdm), select "Weston" as session
- Or test headless: `weston --backend=headless --renderer=gl --socket=wayland-test >/dev/null 2>&1 &`
- If headless works, test wf-recorder:
  ```
  WAYLAND_DISPLAY=wayland-test timeout 5 wf-recorder -f /tmp/wl_test.mp4 -c h264_vaapi -x yuv420p >/dev/null 2>&1 &
  ```

### 5. Verify
```
ffprobe /tmp/wl_test.mp4 2>&1 | grep -i "Stream\|Duration"
cat /sys/class/drm/card*/device/gpu_busy_percent
```

### 6. Document
Write `wayland-setup.md` with:
- What was installed
- Whether the session file exists
- Whether headless Weston + wf-recorder works
- Steps to use Weston session
- Any issues encountered

## Self-command
After reading, execute the steps immediately. ALL commands >/dev/null 2>&1 &. Self-wake to check progress.
