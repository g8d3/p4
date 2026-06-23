#!/bin/bash
# generate_narration.sh - Generate TTS narration for the comparison video

set -euo pipefail

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="$WORKDIR/output"

# Read metrics
DEEPSEEK_JSON="$OUTPUT_DIR/metrics/deepseek.json"
MIMO_JSON="$OUTPUT_DIR/metrics/mimo.json"

DS_DUR=$(python3 -c "import json; d=json.load(open('$DEEPSEEK_JSON')); print(d['duration_sec'])")
DS_TPS=$(python3 -c "import json; d=json.load(open('$DEEPSEEK_JSON')); print(d['tokens_per_sec'])")
DS_COST=$(python3 -c "import json; d=json.load(open('$DEEPSEEK_JSON')); print(d['cost'])")
DS_OUT=$(python3 -c "import json; d=json.load(open('$DEEPSEEK_JSON')); print(d['tokens_output'])")

MM_DUR=$(python3 -c "import json; d=json.load(open('$MIMO_JSON')); print(d['duration_sec'])")
MM_TPS=$(python3 -c "import json; d=json.load(open('$MIMO_JSON')); print(d['tokens_per_sec'])")
MM_COST=$(python3 -c "import json; d=json.load(open('$MIMO_JSON')); print(d['cost'])")
MM_OUT=$(python3 -c "import json; d=json.load(open('$MIMO_JSON')); print(d['tokens_output'])")

# Generate narration text in Spanish
NARRATION="Comparación de recursos entre DeepSeek V4 Flash y Mimo 2.5.
Ambos modelos ejecutaron la misma tarea: escribir una función de ordenamiento merge sort en Python.

DeepSeek completó la tarea en $DS_DUR segundos, generando $DS_OUT tokens de salida a una velocidad de $DS_TPS tokens por segundo. Costo: $DS_COST dólares.

Mimo tardó $MM_DUR segundos, generó $MM_OUT tokens de salida a $MM_TPS tokens por segundo. Costo: $MM_COST dólares.

DeepSeek fue más rápido en velocidad de generación, pero Mimo usó menos tokens de salida y tuvo un costo menor. La elección depende de si priorizas velocidad o eficiencia de tokens."

echo "Narration text:"
echo "$NARRATION"
echo ""

# Generate TTS with edge-tts (Colombian voice)
AUDIO_FILE="$OUTPUT_DIR/narration.mp3"
echo "Generating TTS audio..."
edge-tts --voice "es-CO-SalomeNeural" --text "$NARRATION" --write-media "$AUDIO_FILE" 2>/dev/null

echo "Audio generated: $AUDIO_FILE"
ls -lh "$AUDIO_FILE"

# Get audio duration
AUDIO_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$AUDIO_FILE" 2>/dev/null)
echo "Audio duration: ${AUDIO_DUR}s"
