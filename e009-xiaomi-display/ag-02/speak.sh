#!/usr/bin/env bash
set -euo pipefail

TEXT="$1"
./subtitle.sh "$TEXT"

TMPFILE=$(mktemp /tmp/speak-XXXXXX.mp3)
trap 'rm -f "$TMPFILE"' EXIT

timeout 30 edge-tts --voice es-CO-SalomeNeural --text "$TEXT" --write-media "$TMPFILE" >/dev/null 2>&1
ffplay -nodisp -autoexit "$TMPFILE" >/dev/null 2>&1
