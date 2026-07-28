#!/usr/bin/env bash
set -euo pipefail

# KIE Seedream 4.5 Text-to-Image API wrapper
# Requires: KIE_API_KEY environment variable
#
# Usage:
#   ./kie-image.sh "prompt" [aspect_ratio] [quality]
#
# Examples:
#   ./kie-image.sh "a cat wearing a hat"
#   ./kie-image.sh "a cat wearing a hat" "16:9" "ultra"
#   ./kie-image.sh "a cat wearing a hat" "1:1" "basic"

API_BASE="${KIE_API_BASE_URL:-https://api.kie.ai}"
PROMPT="${1:?Usage: kie-image.sh <prompt> [aspect_ratio] [quality]}"
ASPECT_RATIO="${2:-1:1}"
QUALITY="${3:-basic}"

call_api() {
    local endpoint="$1"
    local data="${2:-}"
    local method="${3:-POST}"

    if [ "$method" = "GET" ]; then
        curl -sS "$API_BASE$endpoint" \
            -H "Authorization: Bearer $KIE_API_KEY"
    else
        printf '%s' "$data" | curl -sS "$API_BASE$endpoint" \
            -H "Authorization: Bearer $KIE_API_KEY" \
            -H "Content-Type: application/json" \
            -X "$method" \
            -d @-
    fi
}

echo "=== Creating image task ==="
echo "Prompt: $PROMPT"
echo "Aspect ratio: $ASPECT_RATIO"
echo "Quality: $QUALITY"
echo ""

JSON_DATA=$(cat <<ENDJSON
{
    "model": "seedream/4.5-text-to-image",
    "input": {
        "prompt": "$PROMPT",
        "aspect_ratio": "$ASPECT_RATIO",
        "quality": "$QUALITY",
        "nsfw_checker": false
    }
}
ENDJSON
)

RESPONSE=$(call_api "/api/v1/jobs/createTask" "$JSON_DATA")

echo "Response: $RESPONSE"
echo ""

TASK_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('taskId', ''))" 2>/dev/null || echo "")

if [ -z "$TASK_ID" ]; then
    echo "Error: no taskId in response"
    exit 1
fi

echo "Task ID: $TASK_ID"
echo "Polling for result..."
echo ""

for i in $(seq 1 60); do
    sleep 5

    RESULT=$(call_api "/api/v1/jobs/recordInfo?taskId=$TASK_ID" "" "GET" 2>/dev/null || echo "")

    if [ -z "$RESULT" ]; then
        echo "Query failed, retrying..."
        continue
    fi

    STATE=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('state', ''))" 2>/dev/null || echo "unknown")

    echo "[$i] State: $STATE"

    if [ "$STATE" = "success" ]; then
        echo ""
        echo "=== Result ==="
        echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"

        IMAGE_URLS=$(echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin).get('data', {})
result_json = data.get('resultJson', '{}')
if isinstance(result_json, str):
    result = json.loads(result_json)
else:
    result = result_json
for url in result.get('resultUrls', []):
    print(url)
" 2>/dev/null || echo "")

        if [ -n "$IMAGE_URLS" ]; then
            echo ""
            echo "Image URLs:"
            echo "$IMAGE_URLS"
            echo ""

            SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/output}"
            mkdir -p "$OUTPUT_DIR"
            TIMESTAMP=$(date +%s)
            while IFS= read -r url; do
                if [ -n "$url" ]; then
                    echo "Downloading: $url"
                    curl -sS -o "$OUTPUT_DIR/kie_${TIMESTAMP}_$(basename "$url" | cut -d? -f1)" "$url" &
                fi
            done <<< "$IMAGE_URLS"
            wait
            echo "Saved to $OUTPUT_DIR/"
        fi

        exit 0
    elif [ "$STATE" = "failed" ]; then
        echo ""
        echo "=== Task failed ==="
        echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"
        exit 1
    fi
done

echo "Timeout waiting for task $TASK_ID"
exit 1
