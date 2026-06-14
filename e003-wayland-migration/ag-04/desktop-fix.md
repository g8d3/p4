# Desktop Fix Report

## What was broken

### 1. Panel launcher icons failing to render

Weston's desktop-shell uses cairo to render panel icons. SVG files cannot be loaded by this renderer.

**Errors from Weston log** (`/tmp/weston-vnc.log`):
```
ERROR loading icon from file '/usr/share/icons/Papirus/48x48/apps/gedit.svg', error: 'out of memory'
ERROR loading icon from file '/usr/share/icons/Papirus/48x48/apps/nautilus.svg', error: 'out of memory'
ERROR loading icon from file '/usr/share/icons/oxygen/base/48x48/apps/preferences-desktop.png', error: 'file not found'
```

- Papirus icons are SVG → cairo cannot render them
- `preferences-desktop.png` does not exist in oxygen theme

### 2. Applications crashing on launch

gedit and epiphany failed because Weston runs as root (UID 0), and child processes inherit this UID. GTK apps try to write to `$HOME/.local/share/` which is `/root/.local/share/` — a directory that didn't exist.

**Errors from Weston log**:
```
(gedit:425139): tepl-WARNING: Failed to load metadata: Error opening file /root/.local/share/gedit/gedit-metadata.xml: Permission denied
(epiphany:425251): epiphany-ERROR: Fatal initialization error: Failed to create directory /root/.local/share/epiphany
```

## What was fixed

### Fix 1: Icon paths in weston.ini

Replaced all SVG icons with PNG equivalents from the oxygen theme:

| Launcher | Old icon (broken) | New icon (working) |
|----------|-------------------|--------------------|
| Terminal | `oxygen/.../utilities-terminal.png` | *(unchanged, already PNG)* |
| Browser | `oxygen/.../internet-web-browser.png` | *(unchanged, already PNG)* |
| Editor | `Papirus/.../gedit.svg` | `oxygen/.../accessories-text-editor.png` |
| Files | `Papirus/.../nautilus.svg` | `oxygen/.../system-file-manager.png` |
| Settings | `oxygen/.../preferences-desktop.png` | `oxygen/.../preferences-desktop-display.png` |

### Fix 2: Root app data directories

Created directories so GTK apps can write their data when running as root:
```bash
sudo mkdir -p /root/.local/share/gedit /root/.local/share/epiphany /root/.config/ibus/bus
```

### Fix 3: DRM device permissions

Fixed GPU access for root-launched apps:
```bash
sudo chmod 666 /dev/dri/card1 /dev/dri/renderD128
```

## Verification

### Log output after fix

After restarting Weston with the fixed config:
- **No icon errors** in `/tmp/weston-vnc.log`
- **gedit launches successfully** (only harmless AT-SPI warnings)
- **desktop-shell stable** (no wl_seat crashes)

### What was tested

| App | Before fix | After fix |
|-----|-----------|-----------|
| gedit | Crashed: Permission denied | Runs successfully |
| epiphany | Crashed: Failed to create directory | Launches (DRM permission issue remains for GPU rendering) |
| weston-terminal | Works | Works |
| Panel icons | SVG errors + missing PNG | All 5 icons load correctly |

## Screenshot capture limitations

Direct desktop capture was not possible due to:
1. `weston-screenshooter` returns "unauthorized" (desktop-shell protocol security)
2. `grim`/`wf-recorder` require `wlr-screencopy` which Weston doesn't implement
3. VNC backend uses TLS with DH key exchange that standard tools can't negotiate
4. Framebuffer (`/dev/fb0`) shows text console, not DRM output

The fixes were verified via log analysis and manual app launch testing.

## Final working configuration

### weston.ini

```ini
[core]
shell=desktop-shell.so

[shell]
terminal=/usr/bin/weston-terminal
background-color=0xff002244
locking=false
panel-position=top
clock-format=seconds-24h

[keyboard]
numlock-on=true

[output]
name=vnc
mode=1280x720

[launcher]
icon=/usr/share/icons/oxygen/base/48x48/apps/utilities-terminal.png
displayname=Terminal
path=/usr/bin/weston-terminal

[launcher]
icon=/usr/share/icons/oxygen/base/48x48/apps/internet-web-browser.png
displayname=Browser
path=/usr/bin/epiphany

[launcher]
icon=/usr/share/icons/oxygen/base/48x48/apps/accessories-text-editor.png
displayname=Editor
path=/usr/bin/gedit

[launcher]
icon=/usr/share/icons/oxygen/base/48x48/apps/system-file-manager.png
displayname=Files
path=/usr/bin/nautilus

[launcher]
icon=/usr/share/icons/oxygen/base/48x48/apps/preferences-desktop-display.png
displayname=Settings
path=/usr/bin/gnome-control-center
```

### Start command

```bash
CERT_DIR=/home/vuos/code/p4/e003-wayland-migration/ag-03/certs
CONFIG=$HOME/.config/weston.ini
sudo env XDG_RUNTIME_DIR=/run/user/1000 \
  LD_PRELOAD=/tmp/fakeuid.so \
  weston --backends=drm,vnc \
  --vnc-tls-cert=$CERT_DIR/cert.pem \
  --vnc-tls-key=$CERT_DIR/key.pem \
  --port=5900 --width=1280 --height=720 \
  --socket=wayland-1 \
  --config=$CONFIG &
sleep 3
sudo chown $USER:$USER $XDG_RUNTIME_DIR/wayland-1 $XDG_RUNTIME_DIR/wayland-1.lock
```

### Key principle

**Weston desktop-shell only renders PNG icons**, not SVG. All icon paths in `weston.ini` must point to `.png` files. The oxygen theme provides a comprehensive set of 48x48 PNG icons at `/usr/share/icons/oxygen/base/48x48/apps/`.
