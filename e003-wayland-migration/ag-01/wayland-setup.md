# Wayland Setup — Weston + wf-recorder

## What was installed

All required packages were already installed:

| Package | Version | Status |
|---|---|---|
| `weston` | 13.0.0 | pre-installed |
| `xwayland` | 23.2.6 | pre-installed |
| `wf-recorder` | 0.4.1 | pre-installed |
| `sway` | 1.9 | pre-installed |
| `libwlroots12t64` | 0.17.1 | pre-installed |

No additional packages were needed.

## Session file

`/usr/share/wayland-sessions/weston.desktop` exists with content:

```
[Desktop Entry]
Name=Weston
Comment=The reference Wayland server
Exec=weston
Type=Application
```

This makes "Weston" selectable at the login screen (lightdm/gdm).

## Headless Weston + wf-recorder: FAILS

`wf-recorder` (v0.4.1) requires the `wlr-screencopy-unstable-v1` protocol, which is specific to **wlroots-based compositors** (Sway, Hyprland, etc.). Weston uses `libweston`, not wlroots, so it does not implement this protocol.

Attempting to run `wf-recorder` against a headless Weston produces:

```
compositor doesn't support wlr-screencopy-unstable-v1
```

## Headless Sway (wlroots) + wf-recorder: WORKS

Using Sway (a wlroots compositor, already installed), GPU-direct capture works:

### Software encoding (CPU)
```bash
WLR_BACKENDS=headless sway -c /tmp/sway-config/config -d &
WAYLAND_DISPLAY=wayland-1 wf-recorder -f output.mp4 -c libx264
```

### Hardware encoding (VAAPI, GPU-direct)
```bash
WLR_BACKENDS=headless sway -c /tmp/sway-config/config -d &
WAYLAND_DISPLAY=wayland-1 wf-recorder -f output.mp4 -c h264_vaapi
```

**Verified output**: H.264 (High), 1280x720, yuvj420p, MP4 container.
**DMA-BUF**: Enabled, device `/dev/dri/renderD128` — truly GPU-direct.

Note: The `-x yuv420p` option must **not** be used with VAAPI as it causes a pixel format conversion error.

## Steps to use Weston session at login

1. At the login screen (lightdm/gdm), click the session/settings icon
2. Select **Weston** from the session list
3. Log in — Weston starts as a Wayland compositor
4. Open a terminal (weston-terminal or any Wayland-native terminal)
5. For video capture, note that `wf-recorder` does NOT work in Weston. Use **Sway** instead:
   - Select "Sway" at the login screen (if available), or
   - Use Sway headless for automated capture (see above)

## Issues encountered

1. **wf-recorder + Weston incompatibility**: wf-recorder only supports wlroots-based compositors. Weston is not wlroots-based.
2. **VAAPI pixel format**: Using `-x yuv420p` with `-c h264_vaapi` causes `Impossible to convert between the formats` error. Omit `-x` when using VAAPI hardware encoding.
3. **Headless Sway config**: A minimal config file is required (`output Virtual-1 resolution 1920x1080`) to create a virtual output for capture.
4. **DMA-BUF device mismatch**: When running compositor on a different device than the encoder, wf-recorder falls back to CPU copy. Using `--no-dmabuf` forces CPU copy if needed.

## Recommendation

For GPU-direct video capture:
- Use **Sway** (wlroots-based) as the compositor
- Use `wf-recorder -c h264_vaapi` (without `-x yuv420p`)
- Weston remains available as a general-purpose Wayland compositor session
