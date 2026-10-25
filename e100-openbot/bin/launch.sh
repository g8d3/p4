#!/bin/bash
# Headless OpenBot with a working Secret Service. Mirrors OpenBot's own
# resources/hosting/openbot-container: password file -> --unlock -> --start, default alias = login.
# Dedicated keyring under .keyring-data (gitignored); never touches ~/.local/share/keyrings.
set -euo pipefail
umask 077
D="$(cd "$(dirname "$0")/.." && pwd)"
export XDG_DATA_HOME="$D/.keyring-data"
KR="$XDG_DATA_HOME/keyrings"; ST="$D/.keyring-state"
mkdir -p "$KR" "$ST" "$D/logs"
pkill -f "OpenBot-x86_64.AppImage" 2>/dev/null || true
pkill -f "/tmp/.mount_OpenBo.*/openbot" 2>/dev/null || true
if [ -f "$ST/pids" ]; then kill $(cat "$ST/pids") 2>/dev/null || true; fi
pkill -f "gnome-keyring-daemon.*$D" 2>/dev/null || true
sleep 3
pgrep -f "Xvfb :99" >/dev/null || (Xvfb :99 -screen 0 1280x800x24 -nolisten tcp >/dev/null 2>&1 &)
export DISPLAY=:99
if [ ! -s "$ST/keyring-password" ]; then
  if [ -e "$KR/login.keyring" ]; then echo "keyring exists but password file missing" >&2; exit 1; fi
  head -c 32 /dev/urandom | base64 | tr -d "\n" > "$ST/keyring-password"
fi
printf login > "$KR/default"
eval "$(dbus-launch --sh-syntax)"
export DBUS_SESSION_BUS_ADDRESS DBUS_SESSION_BUS_PID
eval "$(gnome-keyring-daemon --unlock --components=secrets --control-directory="$ST/ctl" < "$ST/keyring-password")"
eval "$(gnome-keyring-daemon --start --components=secrets --control-directory="$ST/ctl")"
export GNOME_KEYRING_CONTROL
printf 'export DISPLAY=:99\nexport DBUS_SESSION_BUS_ADDRESS="%s"\nexport XDG_DATA_HOME="%s"\n' "$DBUS_SESSION_BUS_ADDRESS" "$XDG_DATA_HOME" > "$ST/env"
echo "$DBUS_SESSION_BUS_PID" > "$ST/pids"
nohup "$D/downloads/OpenBot-x86_64.AppImage" --no-sandbox --password-store=gnome-libsecret \
  --remote-debugging-port=9222 --remote-allow-origins=* >> "$D/logs/openbot.log" 2>&1 &
echo "launched pid $!"
