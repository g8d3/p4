# Sway Setup — Weston → Sway Migration

## Migration Commands

### Start Sway (as root, with LD_PRELOAD for UID faking)

```bash
sudo env XDG_RUNTIME_DIR=/run/user/1000 \
  LD_PRELOAD=/tmp/fakeuid.so \
  WLR_DRM_NO_ATOMIC=1 \
  sway -d > /tmp/sway.log 2>&1 &
```

**Critical**: `WLR_DRM_NO_ATOMIC=1` is required. Without it, DRM atomic commit fails with "Permission denied" when running sway as root via SSH session (no graphical seat).

### Fix socket permissions (required after sway starts)

```bash
chmod 777 /run/user/1000/wayland-1
chmod 777 /run/user/1000/sway-ipc.*.sock
```

Sway runs as root, but user processes (waybar, wf-recorder, wayvnc) need socket access.

### Start WayVNC (as root, with auth + TLS)

wayvnc MUST run as root (same UID as Sway) with `--seat seat0` to bind virtual pointer/keyboard protocols. Auth is configured via config file (wayvnc 0.7.2 has no `--auth` CLI flag).

```bash
sudo env WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 \
  wayvnc --seat seat0 -C ~/.config/wayvnc/config 0.0.0.0 5900 > /tmp/wayvnc.log 2>&1 &
```

**Note**: Since wayvnc runs as root, `~` resolves to `/root`. Use `-C /home/vuos/.config/wayvnc/config` if config is in vuos home.

**Input forwarding**: wayvnc binds `zwlr_virtual_pointer_manager_v1` and `zwp_virtual_keyboard_manager_v1` from Sway. These create virtual input devices on seat0 when a VNC client sends mouse/keyboard events.

### WayVNC Security Config

Location: `~/.config/wayvnc/config`

```
address=0.0.0.0
enable_auth=true
username=vuos
password=sway2026
certificate_file=/home/vuos/code/p4/e003-wayland-migration/certs/cert.pem
private_key_file=/home/vuos/code/p4/e003-wayland-migration/certs/key.pem
```

**Security features**:
- **TLS encryption**: VNC traffic encrypted with TLS (cert.pem + key.pem)
- **Username/password auth**: Clients must provide credentials
- **No PAM**: wayvnc 0.7.2 does not support PAM authentication — uses built-in username/password only

**Credentials**: `vuos` / `sway2026`

### Start Waybar

```bash
SWAYSOCK=$(ls /run/user/1000/sway-ipc.*.sock | head -1) \
  WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 \
  DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  waybar > /tmp/waybar.log 2>&1 &
```

### Test wf-recorder

```bash
WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 \
  timeout 5 wf-recorder -f /tmp/test.mp4 -c h264_vaapi
```

## Sway Config File

Location: `~/.config/sway/config`

Key settings:
- `output * resolution 1280x720` — capture resolution for wf-recorder
- `xwayland disable` — saves resources (no X11 apps needed)
- `seat seat0 xcursor_theme Adwaita 24` — cursor theme for VNC
- `exec_always ~/.config/sway/waybar-wrapper.sh` — launches waybar
- `bindsym $mod+Return exec wofi --show drun` — app launcher
- `bindsym $mod+Shift+Return exec foot` — terminal
- `seat seat0 { hide_cursor 0; pointer_deny_drag false; }` — allow virtual input from wayvnc

## WayVNC Setup

- wayvnc 0.7.2 — no TLS via CLI flags (use config file for TLS)
- Listening on `0.0.0.0:5900`
- Output: `HDMI-A-1` (auto-detected, no `--output` flag needed)

## wf-recorder Verification

**Result**: SUCCESS
- `h264_vaapi` encoding via DMA-BUF capture
- Device: `/dev/dri/renderD128` (AMD radeonsi)
- Output: 1920x1080 (native display resolution)
- File size: ~316KB for 5 seconds

## How to Revert to Weston

```bash
# Kill sway
pgrep -f "sway -d" | xargs sudo kill

# Start weston
sudo env XDG_RUNTIME_DIR=/run/user/1000 \
  LD_PRELOAD=/tmp/fakeuid.so \
  weston --backend=drm,vnc --port=5900 > /tmp/weston.log 2>&1 &
```

## Known Issues

1. **Socket permissions**: Sway runs as root (SSH session, no graphical seat), but user processes need socket access. Must `chmod 777` sockets after start.
2. **No seatd/logind seat**: SSH session has no graphical seat. Sway uses embedded seatd with `WLR_DRM_NO_ATOMIC=1`.
3. **wayvnc 0.7.2**: No `--cert`/`--key` CLI flags. TLS requires config file approach. Must run as root with `--seat seat0` for input forwarding.
4. **Input forwarding**: wayvnc binds `zwlr_virtual_pointer_manager_v1` and `zwp_virtual_keyboard_manager_v1`. Virtual devices created on-demand when VNC client sends input. Seat config in sway enables virtual input.
5. **Input device permissions**: `/dev/input/event*` not accessible by vuos user (non-critical for waybar).
6. **Multiple sway instances**: Each `sudo sway` creates a new instance. Kill old ones before starting new.

## File Locations

- Sway config: `~/.config/sway/config`
- Waybar config: `~/.config/waybar/config.jsonc`
- Waybar CSS: `~/.config/waybar/style.css`
- Waybar wrapper: `~/.config/sway/waybar-wrapper.sh`
- Sway log: `/tmp/sway.log`
- wayvnc log: `/tmp/wayvnc.log`
- waybar log: `/tmp/waybar.log`
