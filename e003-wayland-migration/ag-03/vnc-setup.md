# VNC Access to Wayland Desktop

## What was tried

### 1. Weston VNC backend alone (software, works)
`GnuTLS: Failed to load credentials` — certs hadn't been generated. Once certs were created, VNC worked with Pixman (software) renderer.

### 2. Weston DRM + VNC (hardware GPU)
`--backends=drm,vnc` uses radeonsi/AMD GL for the physical monitor + VNC for remote access.

### 3. VNC auth failure
`VNC: wrong user 'vuos'` even with correct password. Root cause: `vnc-backend.so` checks `getpwnam(username)->pw_uid == getuid()`. Since weston runs as root (UID 0) but the VNC user has UID 1000, the check rejects before PAM is consulted. **Fix**: `LD_PRELOAD` to override `getuid()`.

### 4. Terminal doesn't launch
Wayland socket owned by root, non-root processes get `EACCES`. **Fix**: `chown` the socket to the user after startup.

### 5. Waybar panel (incompatible)
Waybar requires `wlr-layer-shell` protocol which Weston's `desktop-shell` does not implement. Weston has its own panel with launcher support via `weston.ini`.

## Working solution

### Prerequisites
- Weston 13.0.0 with `libweston-13-vnc-backend`
- User in `video` group: `sudo usermod -aG video $USER`

### Step 0: PAM config (one-time)
```bash
sudo tee /etc/pam.d/weston-remote-access << 'EOF'
#%PAM-1.0
auth    include common-auth
account include common-account
EOF
```

### Step 1: TLS certs (one-time)
```bash
CERT_DIR=/home/vuos/code/p4/e003-wayland-migration/ag-03/certs
mkdir -p "$CERT_DIR"
openssl req -x509 -newkey rsa:4096 \
  -keyout "$CERT_DIR/key.pem" \
  -out "$CERT_DIR/cert.pem" \
  -days 365 -nodes -subj "/CN=$(hostname)"
chmod 600 "$CERT_DIR/key.pem"
```

### Step 2: Build getuid override (one-time)
```bash
cat > /tmp/fakeuid.c << 'EOF'
#include <unistd.h>
uid_t getuid(void) { return 1000; }
uid_t geteuid(void) { return 1000; }
EOF
gcc -shared -fPIC -o /tmp/fakeuid.so /tmp/fakeuid.c
```
Replace `1000` with `$(id -u)`.

### Step 3: Install apps (one-time)
```bash
sudo apt-get install -y waybar wofi epiphany-browser gedit nautilus thunar
```
Note: Waybar won't work with Weston's shell protocol. The built-in Weston panel is used instead.

### Step 4: Stop the display manager
```bash
sudo systemctl stop sddm
ps aux | grep -E "Xorg|sddm"  # verify stopped
```

### Step 5: Start Weston
```bash
CERT_DIR=/home/vuos/code/p4/e003-wayland-migration/ag-03/certs
CONFIG=$HOME/.config/weston.ini
sudo env XDG_RUNTIME_DIR=/run/user/1000 \
  LD_PRELOAD=/tmp/fakeuid.so \
  weston --backends=drm,vnc \
  --vnc-tls-cert=$CERT_DIR/cert.pem \
  --vnc-tls-key=$CERT_DIR/key.pem \
  --port=5900 --width=1280 --height=720 \
  --config=$CONFIG \
  > /tmp/weston-vnc.log 2>&1 &
sleep 3
sudo chown $USER:$USER $XDG_RUNTIME_DIR/wayland-1 $XDG_RUNTIME_DIR/wayland-1.lock
```

The desktop-shell panel shows launchers for terminal, browser, editor, file manager, and settings. A `weston.ini` template with these launchers is created automatically.

### Step 6: Connect via VNC
| Setting | Value |
|---------|-------|
| Server | `<hostname>:5900` |
| Protocol | VNC with TLS |
| Auth | PAM (your Linux user/pass) |

### Step 7: Stop and revert
```bash
sudo kill $(pgrep -f "weston --backends=")
sudo systemctl start sddm  # back to Xorg
```

### Startup script
`./start-weston.sh` does all steps automatically.

## Notes
- SDDM stop does not kill SSH
- One VNC client at a time
- `LD_PRELOAD` bypasses the UID check in VNC backend
- Wayland socket `chown` enables user app launches
- wofi can be launched from a terminal (`wofi --show drun`)
- Self-signed certs: accept the warning
