#!/bin/bash

# Start Weston with DRM + VNC backends
# Run this after stopping SDDM: sudo systemctl stop sddm

set -e

CERT_DIR="$(dirname "$0")/certs"
CONFIG="$HOME/.config/weston.ini"
SOCK_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}"
USER_UID=$(id -u)

# Ensure weston.ini exists
if [ ! -f "$CONFIG" ]; then
    "$(dirname "$0")/setup-configs.sh"
fi

# Ensure LD_PRELOAD library exists for getuid fix
FAKEUID=/tmp/fakeuid.so
if [ ! -f "$FAKEUID" ]; then
    cat > /tmp/fakeuid.c << 'CEOF'
#include <unistd.h>
uid_t getuid(void) { return 1000; }
uid_t geteuid(void) { return 1000; }
CEOF
    gcc -shared -fPIC -o "$FAKEUID" /tmp/fakeuid.c
fi

# Stop SDDM (Xorg)
sudo systemctl stop sddm 2>/dev/null || true
sleep 2

# Start weston
sudo env XDG_RUNTIME_DIR="$SOCK_DIR" \
  LD_PRELOAD="$FAKEUID" \
  weston --backends=drm,vnc \
  --vnc-tls-cert="$CERT_DIR/cert.pem" \
  --vnc-tls-key="$CERT_DIR/key.pem" \
  --port=5900 \
  --width=1280 --height=720 \
  --config="$CONFIG" \
  > /tmp/weston-vnc.log 2>&1 &

echo "Weston PID: $!"

# Wait for socket, then fix ownership
sleep 3
sudo chown "$USER_UID:$USER_UID" "$SOCK_DIR/wayland-1" "$SOCK_DIR/wayland-1.lock" 2>/dev/null

echo "Wayland socket: $SOCK_DIR/wayland-1"
echo "VNC: port 5900 (TLS)"
echo "Connect: vncviewer --tls <hostname>:5900"
