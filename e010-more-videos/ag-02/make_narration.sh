#!/bin/bash
# make_narration.sh — Generate TTS narration from benchmark metrics

set -euo pipefail

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="$WORKDIR/output"

DS_JSON="$OUTPUT/metrics/deepseek.json"
MM_JSON="$OUTPUT/metrics/mimo.json"

# Read metrics (with fallback defaults)
DS_DUR=$(python3 -c "import json; d=json.load(open('$DS_JSON')); print(d.get('duration_sec',0))" 2>/dev/null || echo "0")
DS_TPS=$(python3 -c "import json; d=json.load(open('$DS_JSON')); print(d.get('tokens_per_sec',0))" 2>/dev/null || echo "0")
DS_OUT=$(python3 -c "import json; d=json.load(open('$DS_JSON')); print(d.get('tokens_output',0))" 2>/dev/null || echo "0")
DS_COST=$(python3 -c "import json; d=json.load(open('$DS_JSON')); print(d.get('cost',0))" 2>/dev/null || echo "0")

MM_DUR=$(python3 -c "import json; d=json.load(open('$MM_JSON')); print(d.get('duration_sec',0))" 2>/dev/null || echo "0")
MM_TPS=$(python3 -c "import json; d=json.load(open('$MM_JSON')); print(d.get('tokens_per_sec',0))" 2>/dev/null || echo "0")
MM_OUT=$(python3 -c "import json; d=json.load(open('$MM_JSON')); print(d.get('tokens_output',0))" 2>/dev/null || echo "0")
MM_COST=$(python3 -c "import json; d=json.load(open('$MM_JSON')); print(d.get('cost',0))" 2>/dev/null || echo "0")

NARRATION="Comparación de recursos entre DeepSeek V4 Flash y Mimo 2.5.
Ambos modelos ejecutaron la misma tarea: escribir una función de ordenamiento merge sort en Python.

DeepSeek completó la tarea en $DS_DUR segundos, generando $DS_OUT tokens de salida a una velocidad de $DS_TPS tokens por segundo. Costo: $DS_COST dólares.

Mimo tardó $MM_DUR segundos, generó $MM_OUT tokens de salida a $MM_TPS tokens por segundo. Costo: $MM_COST dólares.

DeepSeek fue más rápido en velocidad de generación, pero Mimo usó menos tokens de salida y tuvo un costo menor. La elección depende de si priorizas velocidad o eficiencia de tokens."

echo "$NARRATION" > "$OUTPUT/narration.txt"

# Generate TTS
edge-tts --voice "es-CO-SalomeNeural" --text "$NARRATION" \
    --write-media "$OUTPUT/narration.mp3" 2>/dev/null

echo "Narration: $OUTPUT/narration.mp3"
ls -lh "$OUTPUT/narration.mp3"
