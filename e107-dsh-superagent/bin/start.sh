#!/usr/bin/env bash
# e107 superagent panel + remote access.
# Topology:
#   127.0.0.1:3082  dsh --profile superagent (loopback only, per-bundle stateDir)
#   0.0.0.0:8444    socat TLS -> 127.0.0.1:3082 (secure context for remote browsers)
#   0.0.0.0:8091    portal (password + passkey launcher for superagent, no terminal needed)
#   tailnet :9445   tailscale serve -> 127.0.0.1:8444 (panel, trusted cert)
#   tailnet :9446   tailscale serve -> 127.0.0.1:8091 (portal, trusted cert)
# Logs: log/  PIDs: log/*.pid
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LAN_HOST="${1:-$(hostname -I | awk '{print $1}')}"
export OPENCODE_GO_MODEL=muse-spark-1.3-contributor
TS_IP="$(tailscale ip -4 2>/dev/null | head -1 || true)"
PUBLIC_HOST="vuos-hcar5000mi.tail6918b0.ts.net"
DSH_PORT=3082
TLS_PORT=8444
PORTAL_PORT=8091
TS_PANEL_PORT=9445
TS_PORTAL_PORT=9446
E028="$HOME/code/p4/e028-dsh-harness"
PEM="$E028/cert/dsh.pem"
if [[ ! -f "$PEM" ]]; then echo "missing cert $PEM (run e028 bin/gen-cert.sh)" >&2; exit 1; fi
mkdir -p log "$HOME/.dsh/state/superagent"

TRUST_ARGS=(--trusted-host "$LAN_HOST:$TLS_PORT" --trusted-host "$LAN_HOST")
if [[ -n "${TS_IP:-}" && "$TS_IP" != "$LAN_HOST" ]]; then
  TRUST_ARGS+=(--trusted-host "$TS_IP" --trusted-host "$TS_IP:$TLS_PORT")
fi
TRUST_ARGS+=(--trusted-host "$PUBLIC_HOST" --trusted-host "$PUBLIC_HOST:$TS_PANEL_PORT")

if (echo > /dev/tcp/127.0.0.1/$DSH_PORT) 2>/dev/null; then echo "dsh already up on $DSH_PORT, skipping boot"; else
(cd "$E028/app" && nohup npx dsh --profile superagent --patch ../profiles/opencode-default.yml --no-open "${TRUST_ARGS[@]}" >"$ROOT/log/superagent.log" 2>&1 &)
echo $! > "$ROOT/log/superagent.pid"
fi
echo "dsh superagent -> 127.0.0.1:$DSH_PORT (token URL in log/superagent.log — credential, do not paste)"

for i in $(seq 1 30); do
  if (echo > /dev/tcp/127.0.0.1/$DSH_PORT) 2>/dev/null; then break; fi
  sleep 2
done

nohup socat -4 openssl-listen:$TLS_PORT,fork,reuseaddr,cert="$PEM",verify=0 TCP:127.0.0.1:$DSH_PORT >log/socat-tls.log 2>&1 &
echo $! > log/socat.pid
echo "socat tls -> 0.0.0.0:$TLS_PORT"

(cd "$E028/portal" && DSH_LOG="$ROOT/log/superagent.log" DSH_TLS_PORT=$TLS_PORT TS_DSH_PORT=$TS_PANEL_PORT PUBLIC_HOST=$PUBLIC_HOST TS_PORTAL_PORT=$TS_PORTAL_PORT PORTAL_PORT=$PORTAL_PORT nohup node server.mjs >"$ROOT/log/portal.log" 2>&1 &)
echo $! > log/portal.pid
echo "portal -> 0.0.0.0:$PORTAL_PORT (opens panel via live token, never pasted)"

tailscale serve --bg --https=$TS_PANEL_PORT https+insecure://127.0.0.1:$TLS_PORT >/dev/null
tailscale serve --bg --https=$TS_PORTAL_PORT https+insecure://127.0.0.1:$PORTAL_PORT >/dev/null
echo "tailnet panel :$TS_PANEL_PORT -> 127.0.0.1:$TLS_PORT"
echo "tailnet portal :$TS_PORTAL_PORT -> 127.0.0.1:$PORTAL_PORT"
echo
echo "Open (login with portal password/passkey, then Open superagent):"
echo "  https://$PUBLIC_HOST:$TS_PORTAL_PORT"
