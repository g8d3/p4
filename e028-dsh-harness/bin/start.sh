#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# DeepSeek Harness (dsh) web + LAN reverse proxies.
#
# Topology (all verified 2026-08-15):
#   127.0.0.1:3080  dsh web --trusted-host <LAN>:8443
#   0.0.0.0:8080    socat HTTP  -> 127.0.0.1:3080  (plain-LAN browsing, non-privileged APIs)
#   0.0.0.0:8443    socat TLS   -> 127.0.0.1:3080  (secure context: crypto.randomUUID works)
#
# For FULL functionality (settings.*, credentials.*, etc.) use an SSH tunnel
# so the browser origin is loopback:
#   ssh -L 3080:127.0.0.1:3080 <user>@<LAN>  then open http://127.0.0.1:3080

LAN_HOST="${1:-192.168.0.93}"
HTTP_PORT=8080
TLS_PORT=8443
DSH_PORT=3080
PEM="$(bin/gen-cert.sh "$LAN_HOST")"
LOG_DIR=log

mkdir -p "$LOG_DIR"

if ! command -v socat >/dev/null; then
  echo "socat not installed" >&2
  exit 1
fi

if [[ ! -d app/node_modules ]]; then
  echo "app/ not installed — run bin/install.sh first" >&2
  exit 1
fi
(cd app && nohup npx dsh web --trusted-host "$LAN_HOST:$TLS_PORT" >"../$LOG_DIR/dsh.log" 2>&1) &
echo "dsh  -> 127.0.0.1:$DSH_PORT (log: $LOG_DIR/dsh.log)"

sleep 8
nohup socat -4 TCP-LISTEN:$HTTP_PORT,fork,reuseaddr TCP:127.0.0.1:$DSH_PORT >"$LOG_DIR/socat-http.log" 2>&1 &
echo "socat http -> 0.0.0.0:$HTTP_PORT (log: $LOG_DIR/socat-http.log)"

nohup socat -4 openssl-listen:$TLS_PORT,fork,reuseaddr,cert="$PEM",verify=0 TCP:127.0.0.1:$DSH_PORT >"$LOG_DIR/socat-tls.log" 2>&1 &
echo "socat tls  -> 0.0.0.0:$TLS_PORT (log: $LOG_DIR/socat-tls.log)"
echo
echo "Open:"
echo "  http://$LAN_HOST:$HTTP_PORT   (plain HTTP; privileged APIs 403 by design)"
echo "  https://$LAN_HOST:$TLS_PORT   (secure context; accept self-signed cert)"
echo "  ssh -L $DSH_PORT:127.0.0.1:$DSH_PORT <user>@$LAN_HOST  + http://127.0.0.1:$DSH_PORT  (full)"
