#!/usr/bin/env bash
set -euo pipefail

# Deepgram Aura-2 TTS wrapper — REST /v1/speak
# Requires: DEEPGRAM_API_KEY
# p4 convention: MP3 output (default), matching the rest of the pipeline.
#
# Usage:
#   ./dg-tts.sh [options] "<text>"
#
# Options:
#   --voice, -v   Model name (default: aura-2-celeste-es — es-co Colombian)
#   --speed       Speaking rate 0.7-1.5 (Spanish: keep >= 0.9)
#   --out, -o     Output file (default: dg-tts_<ts>.mp3)
#   --wav         Output WAV instead (container=wav, encoding=linear16)
#   --list        List available Spanish models
#   --quiet, -q   Machine-readable output (path only)

API_BASE="https://api.deepgram.com/v1/speak"
VOICE="aura-2-celeste-es"
SPEED="1.0"
OUT=""
QUIET=false
FMT="mp3"

LIST_MODELS() {
  cat <<'EOF'
Spanish Aura-2 voices (es):
  aura-2-agustina-es  aura-2-alvaro-es  aura-2-antonia-es  aura-2-aquila-es*
  aura-2-carina-es*   aura-2-celeste-es (es-co, Colombian)  aura-2-diana-es*
  aura-2-estrella-es  aura-2-gloria-es  aura-2-javier-es*  aura-2-luciano-es
  aura-2-nestor-es    aura-2-olivia-es  aura-2-selena-es*  aura-2-silvia-es
  aura-2-sirio-es     aura-2-valerio-es
  * = codeswitching voice (es/en)
Featured: aura-2-celeste-es (es-co, Clear/Energetic/Friendly)
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --voice|-v) VOICE="$2"; shift 2 ;;
    --speed) SPEED="$2"; shift 2 ;;
    --out|-o) OUT="$2"; shift 2 ;;
    --wav) FMT="wav"; shift ;;
    --list) LIST_MODELS; exit 0 ;;
    --quiet|-q) QUIET=true; shift ;;
    *) TEXT="$1"; shift ;;
  esac
done

[ -n "${TEXT:-}" ] || { echo "error: no text given" >&2; exit 1; }
[ -n "${DEEPGRAM_API_KEY:-}" ] || { echo "error: DEEPGRAM_API_KEY not set" >&2; exit 1; }

if [ -z "$OUT" ]; then
  OUT="dg-tts_$(date +%s%3N).${FMT}"
fi

if [ "$FMT" = "wav" ]; then
  FMT_PARAMS="encoding=linear16&container=wav&sample_rate=24000"
else
  # MP3 is Deepgram's default (encoding=mp3) — no container/encoding params needed.
  FMT_PARAMS=""
fi

if [ -n "$FMT_PARAMS" ]; then
  URL="${API_BASE}?model=${VOICE}&${FMT_PARAMS}&speed=${SPEED}"
else
  URL="${API_BASE}?model=${VOICE}&speed=${SPEED}"
fi

curl -s "${URL}" \
  -H "Authorization: Token ${DEEPGRAM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1]}))' "$TEXT")" \
  -o "$OUT"

if $QUIET; then
  echo "$OUT"
else
  echo "Saved: $OUT"
fi
