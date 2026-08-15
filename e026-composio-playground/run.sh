#!/usr/bin/env bash
# Run the Composio + Deepgram transcription demo.
set -euo pipefail
cd "$(dirname "$0")"
source ~/.zshrc
exec .venv/bin/python bin/transcribe.py "$@"
