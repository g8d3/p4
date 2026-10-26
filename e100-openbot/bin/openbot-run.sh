#!/bin/bash
# Headless OpenBot with a working Secret Service. Mirrors OpenBot's own
# resources/hosting/openbot-container: password file -> --unlock -> --start, default alias = login.
# Dedicated keyring under .keyring-data (gitignored); never touches ~/.local/share/keyrings.
set -euo pipefail
umask 077
D="$(cd "$(dirname "$0")/.." && pwd)"
export XDG_DATA_HOME="$D/.keyring-data"
KR="$XDG_DATA_HOME/keyrings"; ST="$D/.keyring-state"
# OpenGateway provider (Deep / Glim agents): key from private env file, provider from repo config.
if [ -r "$HOME/.secrets/opengateway.env" ]; then set -a; . "$HOME/.secrets/opengateway.env"; set +a; fi
export OPENCODE_CONFIG="$D/opencode.opengateway.json"
mkdir -p "$KR" "$ST" "$D/logs"
if [ ! -s "$ST/keyring-password" ]; then
  if [ -e "$KR/login.keyring" ]; then echo "keyring exists but password file missing" >&2; exit 1; fi
  head -c 32 /dev/urandom | base64 | tr -d "\n" > "$ST/keyring-password"
fi
printf login > "$KR/default"
export DBUS_SESSION_BUS_ADDRESS
eval "$(gnome-keyring-daemon --unlock --components=secrets --control-directory="$ST/ctl" < "$ST/keyring-password")"
eval "$(gnome-keyring-daemon --start --components=secrets --control-directory="$ST/ctl")"
export GNOME_KEYRING_CONTROL
printf 'export WAYLAND_DISPLAY=$WAYLAND_DISPLAY\nexport DBUS_SESSION_BUS_ADDRESS="%s"\nexport XDG_DATA_HOME="%s"\n' "$DBUS_SESSION_BUS_ADDRESS" "$XDG_DATA_HOME" > "$ST/env"
exec "$D/downloads/OpenBot-x86_64.AppImage" --no-sandbox --password-store=gnome-libsecret \
  --remote-debugging-port=9222 --remote-allow-origins=* \
  ${OPENBOT_OZONE:---ozone-platform=wayland --enable-features=UseOzonePlatform,WaylandWindowDecorations} --disable-dev-shm-usage \\
  --force-device-scale-factor=1 >> "$D/logs/openbot.log" 2>&1
