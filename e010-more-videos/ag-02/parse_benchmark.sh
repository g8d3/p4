#!/bin/bash
# parse_benchmark.sh — Parse opencode run output into metrics JSON
# Usage: ./parse_benchmark.sh <output_file> <metrics_json> <provider_model>

set -euo pipefail

OUTPUT_FILE="${1:?Usage: $0 <output_file> <metrics_json> <provider_model>}"
METRICS_JSON="${2:?}"
PROVIDER_MODEL="${3:?}"

PROVIDER="${PROVIDER_MODEL%%/*}"
MODEL="${PROVIDER_MODEL#*/}"

# Try to find step_finish event for token counts
STEP_FINISH=$(grep '"type":"step_finish"' "$OUTPUT_FILE" 2>/dev/null | tail -1 || true)

if [ -n "$STEP_FINISH" ]; then
    TOKENS_TOTAL=$(echo "$STEP_FINISH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('part',{}).get('tokens',{}).get('total',0))" 2>/dev/null || echo "0")
    TOKENS_INPUT=$(echo "$STEP_FINISH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('part',{}).get('tokens',{}).get('input',0))" 2>/dev/null || echo "0")
    TOKENS_OUTPUT=$(echo "$STEP_FINISH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('part',{}).get('tokens',{}).get('output',0))" 2>/dev/null || echo "0")
    TOKENS_REASONING=$(echo "$STEP_FINISH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('part',{}).get('tokens',{}).get('reasoning',0))" 2>/dev/null || echo "0")
    COST=$(echo "$STEP_FINISH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('part',{}).get('cost',0))" 2>/dev/null || echo "0")
else
    TOKENS_TOTAL=0; TOKENS_INPUT=0; TOKENS_OUTPUT=0; TOKENS_REASONING=0; COST=0
fi

# Get text output
OUTPUT_TEXT=$(grep '"type":"text"' "$OUTPUT_FILE" 2>/dev/null | head -1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('part',{}).get('text','')[:500])" 2>/dev/null || echo "")

# Get file stats
FILE_SIZE=$(stat -c%s "$OUTPUT_FILE" 2>/dev/null || stat -f%z "$OUTPUT_FILE" 2>/dev/null || echo "0")
LINE_COUNT=$(wc -l < "$OUTPUT_FILE" 2>/dev/null || echo "0")

# Calculate duration from first and last event timestamps
DURATION_SEC=$(python3 -c "
import json, sys
lines = open('$OUTPUT_FILE').readlines()
first_ts = None
last_ts = None
for line in lines:
    try:
        d = json.loads(line.strip())
        ts = d.get('timestamp', 0)
        if ts > 0:
            if first_ts is None: first_ts = ts
            last_ts = ts
    except: pass
if first_ts and last_ts and last_ts > first_ts:
    print(round((last_ts - first_ts) / 1000.0, 2))
else:
    print(5)
" 2>/dev/null || echo "5")

# Calculate tokens/sec
if [ "$DURATION_SEC" -gt 0 ] 2>/dev/null; then
    TOKENS_PER_SEC=$(python3 -c "print(round($TOKENS_OUTPUT / max($DURATION_SEC, 0.1), 2))" 2>/dev/null || echo "0")
else
    TOKENS_PER_SEC=0
fi

# Write metrics JSON
python3 -c "
import json
data = {
    'provider': '$PROVIDER',
    'model': '$MODEL',
    'provider_model': '$PROVIDER_MODEL',
    'task': 'merge sort with type hints',
    'duration_sec': $DURATION_SEC,
    'tokens_total': $TOKENS_TOTAL,
    'tokens_input': $TOKENS_INPUT,
    'tokens_output': $TOKENS_OUTPUT,
    'tokens_reasoning': $TOKENS_REASONING,
    'tokens_per_sec': $TOKENS_PER_SEC,
    'cost': $COST,
    'file_size': $FILE_SIZE,
    'line_count': $LINE_COUNT,
    'output_text': $(python3 -c "import json; print(json.dumps('''$(echo "$OUTPUT_TEXT" | head -c 400)'''))")
}
with open('$METRICS_JSON', 'w') as f:
    json.dump(data, f, indent=2)
print(json.dumps(data, indent=2))
"
