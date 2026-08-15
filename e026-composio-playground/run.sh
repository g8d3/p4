#!/usr/bin/env bash
# Transcribe a public audio URL via Deepgram directly.
set -euo pipefail
cd "$(dirname "$0")"
[ -f "$HOME/.secrets/.env" ] && set -a && source "$HOME/.secrets/.env" && set +a
exec python3 bin/transcribe_direct.py "$@"
