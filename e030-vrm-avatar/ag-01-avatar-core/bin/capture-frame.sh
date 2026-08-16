#!/usr/bin/env bash
# capture-frame.sh — screenshot a running Chrome tab via CDP into an output path.
#
# Usage:
#   bin/capture-frame.sh <output.png> [url-substring]
#
# Target discovery:
#   1. Chrome must run with --remote-debugging-port (default 9222). Find it with:
#        ss -tln | grep 9222
#   2. The page target is discovered from http://127.0.0.1:<port>/json/list,
#      matched by url-substring (default: "127.0.0.1:8787").
#   3. Screenshot via CDP Page.captureScreenshot (base64 PNG), written to output.
set -euo pipefail

OUT="${1:?usage: capture-frame.sh <output.png> [url-substring]}"
URL_MATCH="${2:-127.0.0.1:8787}"
PORT="${CDP_PORT:-9222}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$(dirname "$OUT")"
node "$DIR/capture-frame.js" --port "$PORT" --match "$URL_MATCH" --out "$OUT"