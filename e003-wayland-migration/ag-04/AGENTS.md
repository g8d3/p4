# ag-04 — Visual desktop repair (multimodal)

## Model
`opencode-go/mimo-v2.5` (has vision)

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, self-wake pattern
- [../ag-03/AGENTS.md](../ag-03/AGENTS.md) — current Weston/VNC setup
- [../ag-03/vnc-setup.md](../ag-03/vnc-setup.md) — VNC documentation

## Goal

Visually inspect the Weston Wayland desktop (via VNC/DRM) using vision model, find and fix display problems (missing icons, broken app launchers, panel issues).

## Context

- Weston running with `--backends=drm,vnc` on socket `wayland-1`, port 5900
- Waybar panel installed with launchers: terminal (works), browser (broken), editor (works), files (unknown)
- Some icons don't render (show placeholder/broken image)
- Weston runs as root with LD_PRELOAD for UID fix
- VNC accessible on port 5900

## Task

### 1. Capture the Wayland desktop

Take a screenshot of the running Weston session:
```bash
WAYLAND_DISPLAY=wayland-1 weston-screenshooter /tmp/weston-screen.png 2>/dev/null
```
If weston-screenshooter doesn't work, try:
```bash
# Capture via wf-recorder single frame
WAYLAND_DISPLAY=wayland-1 timeout 3 wf-recorder -f /tmp/weston-capture.png -c png
```
Or use a VNC-based capture with `vncsnapshot`.

### 2. Visually inspect the screenshot

Read the captured image. Look for:
- Are Waybar icons rendering correctly?
- Is the terminal icon there?
- Is the browser icon broken?
- Is the editor icon there?
- Is there any error overlay or missing elements?

### 3. Diagnose and fix issues

Based on what you see:

**Broken icons**: Check if the icon theme is installed:
```bash
ls /usr/share/icons/*/48x48/apps/ 2>/dev/null | head -20
```
Install missing icon theme: `papirus-icon-theme` or `adwaita-icon-theme`.
Fix Waybar config to use correct icon names.

**Browser not launching**: 
- Check if browser is installed (`which epiphany firefox chromium`)
- Install one: `sudo apt-get install -y epiphany-browser`
- Check Waybar config launcher command

**App launching in general**:
- Verify apps can launch via `WAYLAND_DISPLAY=wayland-1 <app>`
- Check if apps need XWayland (install xwayland if needed)

### 4. Fix and verify iteratively

Fix → capture screenshot → inspect → fix again until the desktop looks correct.

### 5. Document

Write `desktop-fix.md` with:
- What was broken (with screenshots reference)
- What was fixed
- Final working configuration
- Waybar config file content

## Self-command
After reading, execute immediately. ALL commands: `>/dev/null 2>&1 &`. Self-wake to continue.
