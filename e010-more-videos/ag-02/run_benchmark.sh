#!/bin/bash
# run_benchmark.sh - Run a task on a specific provider and collect metrics
# Usage: ./run_benchmark.sh <provider/model> <task> <output_json>
#
# Outputs JSON with: provider, model, duration_ms, tokens_total, tokens_input,
# tokens_output, tokens_reasoning, cost, output_text

set -euo pipefail

PROVIDER_MODEL="${1:?Usage: $0 <provider/model> <task> <output_json>}"
TASK="${2:?Usage: $0 <provider/model> <task> <output_json>}"
OUTPUT_JSON="${3:?Usage: $0 <provider/model> <task> <output_json>}"

TMPDIR="$(mktemp -d)"
RAW_OUTPUT="$TMPDIR/raw.jsonl"
METRICS="$OUTPUT_JSON"

# Split provider/model
PROVIDER="${PROVIDER_MODEL%%/*}"
MODEL="${PROVIDER_MODEL#*/}"

echo "=== Benchmarking $PROVIDER_MODEL ==="
echo "Task: $TASK"

# Record start time with nanosecond precision
START_NS=$(date +%s%N)

# Run opencode and capture JSON events
timeout 120 opencode run -m "$PROVIDER_MODEL" --format json "$TASK" 2>/dev/null > "$RAW_OUTPUT" || true

END_NS=$(date +%s%N)

# Calculate duration
DURATION_MS=$(( (END_NS - START_NS) / 1000000 ))

# Parse the last step_finish event for token counts
STEP_FINISH=$(grep '"type":"step_finish"' "$RAW_OUTPUT" | tail -1)

if [ -n "$STEP_FINISH" ]; then
    TOKENS_TOTAL=$(echo "$STEP_FINISH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['part']['tokens']['total'])" 2>/dev/null || echo "0")
    TOKENS_INPUT=$(echo "$STEP_FINISH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['part']['tokens']['input'])" 2>/dev/null || echo "0")
    TOKENS_OUTPUT=$(echo "$STEP_FINISH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['part']['tokens']['output'])" 2>/dev/null || echo "0")
    TOKENS_REASONING=$(echo "$STEP_FINISH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['part']['tokens'].get('reasoning', 0))" 2>/dev/null || echo "0")
    COST=$(echo "$STEP_FINISH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['part'].get('cost', 0))" 2>/dev/null || echo "0")
else
    TOKENS_TOTAL=0
    TOKENS_INPUT=0
    TOKENS_OUTPUT=0
    TOKENS_REASONING=0
    COST=0
fi

# Get the text output
OUTPUT_TEXT=$(grep '"type":"text"' "$RAW_OUTPUT" | head -1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['part']['text'][:500])" 2>/dev/null || echo "")

# Calculate tokens/sec (output tokens / duration in seconds)
if [ "$DURATION_MS" -gt 0 ]; then
    TOKENS_PER_SEC=$(python3 -c "print(round($TOKENS_OUTPUT / ($DURATION_MS / 1000.0), 2))")
else
    TOKENS_PER_SEC=0
fi

# Write output JSON
python3 -c "
import json, sys
data = {
    'provider': '$PROVIDER',
    'model': '$MODEL',
    'provider_model': '$PROVIDER_MODEL',
    'task': '''$TASK''',
    'duration_ms': $DURATION_MS,
    'duration_sec': round($DURATION_MS / 1000.0, 2),
    'tokens_total': $TOKENS_TOTAL,
    'tokens_input': $TOKENS_INPUT,
    'tokens_output': $TOKENS_OUTPUT,
    'tokens_reasoning': $TOKENS_REASONING,
    'tokens_per_sec': $TOKENS_PER_SEC,
    'cost': $COST,
    'output_text': $(python3 -c "import json; print(json.dumps('''$(echo "$OUTPUT_TEXT" | head -c 400)'''))")
}
with open('$METRICS', 'w') as f:
    json.dump(data, f, indent=2)
print(json.dumps(data, indent=2))
"

# Cleanup
rm -rf "$TMPDIR"
