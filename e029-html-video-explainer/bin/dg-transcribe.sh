#!/usr/bin/env bash
set -euo pipefail

# Deepgram Nova-3 transcription wrapper — REST /v1/listen
# Requires: DEEPGRAM_API_KEY
#
# Transcribes an audio file and writes word-level timestamps. The p4 video
# pipeline REQUIRES transcription of generated audio before building captions
# (captions.mjs reads audio_meta.json -> voices[].words).
#
# Usage:
#   ./dg-transcribe.sh [options] <audio-file> [output.json]
#
# Options:
#   --language, -l   BCP-47 (default: es)
#   --model, -m      nova-3 | nova-2 (default: nova-3)
#   --no-punctuate   Skip smart_format/punctuate (default: on)
#   --quiet, -q      Machine-readable output (transcript JSON path only)

API_BASE="https://api.deepgram.com/v1/listen"
LANG="es"
MODEL="nova-3"
SMART="true"
QUIET=false

while [ $# -gt 0 ]; do
  case "$1" in
    --language|-l) LANG="$2"; shift 2 ;;
    --model|-m) MODEL="$2"; shift 2 ;;
    --no-punctuate) SMART="false"; shift ;;
    --quiet|-q) QUIET=true; shift ;;
    *.wav|*.mp3|*.m4a|*.ogg|*.flac|*.mp4|*.mov|*.webm) AUDIO="$1"; shift ;;
    *.json|*.txt) OUT="$1"; shift ;;
    *) echo "error: unknown arg $1" >&2; exit 1 ;;
  esac
done

[ -n "${AUDIO:-}" ] || { echo "error: no audio file given" >&2; exit 1; }
[ -n "${DEEPGRAM_API_KEY:-}" ] || { echo "error: DEEPGRAM_API_KEY not set" >&2; exit 1; }

if [ -z "${OUT:-}" ]; then
  OUT="dg-transcript_$(date +%s%3N).json"
fi

# Smart formatting + punctuation ON by default (Nova-3 supports both).
curl -s "${API_BASE}?model=${MODEL}&language=${LANG}&smart_format=${SMART}&punctuate=${SMART}" \
  -H "Authorization: Token ${DEEPGRAM_API_KEY}" \
  -H "Content-Type: $(file --brief --mime-type "$AUDIO")" \
  --data-binary @"$AUDIO" -o "$OUT"

if $QUIET; then
  echo "$OUT"
else
  echo "Saved: $OUT"
fi
