#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

HOST="${1:-192.168.0.93}"
CERT_DIR=cert
KEY="$CERT_DIR/dsh-key.pem"
CERT_FILE="$CERT_DIR/dsh-cert.pem"
PEM="$CERT_DIR/dsh.pem"

mkdir -p "$CERT_DIR"
if [[ ! -f "$PEM" ]]; then
  openssl req -x509 -newkey rsa:2048 -keyout "$KEY" -out "$CERT_FILE" \
    -days 365 -nodes -subj "/CN=$HOST"
  cat "$CERT_FILE" "$KEY" > "$PEM"
fi
echo "$PEM"
