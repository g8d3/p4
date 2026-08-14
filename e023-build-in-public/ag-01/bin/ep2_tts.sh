#!/bin/bash
# E02 TTS generation: 12 chunks, identical voice/context params, one pass.
set -u
export KIE_API_KEY
KIE=/home/vuos/code/p4/e019-kie-image-api/ag-01/bin/kie-tts.sh
cd /home/vuos/code/p4/e023-build-in-public/ag-01/output/ep2_tts

VOICE="Kore"
SCENE="A quiet recording studio with soft lighting"
CTX="Clear, patient, educational narrator explaining data analysis with calm enthusiasm and honesty. A teacher speaking to a beginner audience."
STYLE="Vocal Smile"
ACCENT="Neutral"
PACE="Natural"

for i in $(seq -w 0 11); do
  TXT=$(cat "chunk_$i.txt")
  echo "=== chunk $i ==="
  OUT=$(OUTPUT_DIR="$PWD" "$KIE" --voice "$VOICE" --scene "$SCENE" --context "$CTX" \
        --style "$STYLE" --accent "$ACCENT" --pace "$PACE" --quiet --tag "ep2_$i" "$TXT" 2>> tts_err.log)
  echo "chunk $i -> $OUT"
done
echo "TTS DONE"
