#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# DeepSeek Harness (dsh) web + any-IP reverse proxies.
#
# Topology (verified 2026-08-15, refreshed 2026-10-18 for dsh 0.2.1-rc.2):
#   127.0.0.1:3080  dsh web --trusted-host <each entry-point authority>
#   0.0.0.0:8080    socat HTTP  -> 127.0.0.1:3080  (plain LAN/tailnet, trusted-LAN-only)
#   0.0.0.0:8443    socat TLS   -> 127.0.0.1:3080  (secure context for any-IP browsers)
#   0.0.0.0:8090    portal (password + passkey launcher, no terminal needed)
#   tailnet :9443   tailscale serve -> 127.0.0.1:8090 (portal, trusted cert)
#   tailnet :9444   tailscale serve -> 127.0.0.1:8443 (dsh, trusted cert)
#
# dsh 0.2.1-rc.2 could bind a LAN IP natively (--host takes one interface
# literal now) and even terminate TLS itself, but the socat topology stays:
# one dsh boot = one launch token, and socat keeps a single origin server
# for HTTP + TLS + tailnet-serve at once.
#
# For a loopback origin from another machine (full functionality without
# trusting extra hosts):
#   ssh -L 3080:127.0.0.1:3080 <user>@<LAN>  then open http://127.0.0.1:3080

LAN_HOST="${1:-$(hostname -I | awk '{print $1}')}"
# Service model pin (2026-10-18): platform env still exports 1.2; run 1.3.
# Delete this line to follow the platform value again.
export OPENCODE_GO_MODEL=muse-spark-1.3-contributor
TS_IP="$(tailscale ip -4 2>/dev/null | head -1 || true)"
PUBLIC_HOST="$(node -e "try{console.log(require('./needs.json').public_host)}catch(e){}" 2>/dev/null || true)"
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
# Trust every authority a browser may present: LAN + tailnet IPs (any port
# via bare-host form, plus explicit ports for the documented entries) and
# the tailnet MagicDNS name served by `tailscale serve` on :9444.
TRUST_ARGS=(--trusted-host "$LAN_HOST:$TLS_PORT" --trusted-host "$LAN_HOST:$HTTP_PORT")
TRUST_ARGS+=(--trusted-host "$LAN_HOST")
if [[ -n "${TS_IP:-}" && "$TS_IP" != "$LAN_HOST" ]]; then
  TRUST_ARGS+=(--trusted-host "$TS_IP" --trusted-host "$TS_IP:$TLS_PORT" --trusted-host "$TS_IP:$HTTP_PORT")
fi
if [[ -n "${PUBLIC_HOST:-}" ]]; then
  TRUST_ARGS+=(--trusted-host "$PUBLIC_HOST" --trusted-host "$PUBLIC_HOST:9444")
fi
# Default provider+model come from profiles/opencode-default.yml (OPENCODE_* env).
# NOTE: --patch is a launcher flag: it goes with --profile, not after `web`.
(cd app && nohup npx dsh --profile web --patch ../profiles/opencode-default.yml --no-open "${TRUST_ARGS[@]}" >"../$LOG_DIR/dsh.log" 2>&1) &
echo "dsh  -> 127.0.0.1:$DSH_PORT (token URL in $LOG_DIR/dsh.log — that URL is a credential, do not paste it into chats/logs)"

sleep 8
nohup socat -4 TCP-LISTEN:$HTTP_PORT,fork,reuseaddr TCP:127.0.0.1:$DSH_PORT >"$LOG_DIR/socat-http.log" 2>&1 &
echo "socat http -> 0.0.0.0:$HTTP_PORT (log: $LOG_DIR/socat-http.log)"

nohup socat -4 openssl-listen:$TLS_PORT,fork,reuseaddr,cert="$PEM",verify=0 TCP:127.0.0.1:$DSH_PORT >"$LOG_DIR/socat-tls.log" 2>&1 &
echo "socat tls  -> 0.0.0.0:$TLS_PORT (log: $LOG_DIR/socat-tls.log)"

PORTAL_PORT=8090
if [[ -f portal/.pass.json ]]; then
  (cd portal && PORTAL_PORT=$PORTAL_PORT nohup node server.mjs >"../$LOG_DIR/portal.log" 2>&1 &) 
  echo "portal   -> https://$LAN_HOST:$PORTAL_PORT (password-gated launcher, no terminal needed)"
else
  echo "portal skipped: portal/.pass.json missing" >&2
fi
echo
echo "Open:"
echo "  http://$LAN_HOST:$HTTP_PORT   (plain HTTP; privileged APIs 403 by design)"
echo "  https://$LAN_HOST:$TLS_PORT   (secure context; accept self-signed cert)"
echo "  ssh -L $DSH_PORT:127.0.0.1:$DSH_PORT <user>@$LAN_HOST  + http://127.0.0.1:$DSH_PORT  (full)"
