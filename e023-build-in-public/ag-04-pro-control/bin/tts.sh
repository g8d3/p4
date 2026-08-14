#!/bin/bash
# E03 (Pro control) TTS: 12 chunks, identical Alnilam voice/context params, one pass.
set -u
export KIE_API_KEY
KIE=/home/vuos/code/p4/e019-kie-image-api/ag-01/bin/kie-tts.sh
TTSDIR=/home/vuos/code/p4/e023-build-in-public/ag-04-pro-control/output/tts
cd "$TTSDIR"

VOICE="Alnilam"
SCENE="A quiet recording studio with soft lighting"
CTX="Clear, patient, educational narrator explaining data analysis with calm honesty. A teacher speaking to a beginner audience."
STYLE="Vocal Smile"
ACCENT="Neutral"
PACE="Natural"

> tts_paths.txt
for i in $(seq -w 0 11); do
  TXT=$(cat "chunk_$i.txt")
  echo "=== chunk $i ($(wc -w <<< "$TXT") words) ==="
  OUT=$(OUTPUT_DIR="$PWD" "$KIE" --voice "$VOICE" --scene "$SCENE" --context "$CTX" \
        --style "$STYLE" --accent "$ACCENT" --pace "$PACE" --quiet --tag "e03_$i" "$TXT" 2>> tts_err.log)
  echo "chunk $i -> $OUT"
  echo "$i $OUT" >> tts_paths.txt
  DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUT" 2>/dev/null)
  echo "  dur=${DUR}s"
done
echo "TTS DONE"
