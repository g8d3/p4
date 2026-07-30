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
QUIET=false
TAG=""
IMAGE_URL=""
MODEL="seedream/4.5-text-to-image"

while [ $# -gt 0 ]; do
    case "$1" in
        --quiet|-q) QUIET=true; shift ;;
        --tag|-t) TAG="$2"; shift 2 ;;
        --image-url|-i) IMAGE_URL="$2"; MODEL="seedream/5-pro-image-to-image"; shift 2 ;;
        --model|-m) MODEL="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: kie-image.sh [options] <prompt> [aspect_ratio] [quality]"
            echo "  --quiet, -q       Machine-readable output (only URL on success)"
            echo "  --tag, -t         Tag for output filename"
            echo "  --image-url, -i   Input image URL (image-to-image mode)"
            echo "  --model, -m       Model override (default: seedream/4.5-text-to-image)"
            exit 0 ;;
        *) break ;;
    esac
done

PROMPT="${1:?Usage: kie-image.sh [options] <prompt> [aspect_ratio] [quality]}"
ASPECT_RATIO="${2:-1:1}"
QUALITY="${3:-basic}"

call_api() {
    local endpoint="$1"
    local data="${2:-}"
    local method="${3:-POST}"
    local response
    local http_code

    if [ "$method" = "GET" ]; then
        response=$(curl -sS -w "\n%{http_code}" "$API_BASE$endpoint" \
            -H "Authorization: Bearer $KIE_API_KEY")
    else
        response=$(printf '%s' "$data" | curl -sS -w "\n%{http_code}" "$API_BASE$endpoint" \
            -H "Authorization: Bearer $KIE_API_KEY" \
            -H "Content-Type: application/json" \
            -X "$method" \
            -d @-)
    fi

    http_code=$(echo "$response" | tail -1)
    local body
    body=$(echo "$response" | sed '$d')

    # Rate limit (433) — wait and retry once
    if [ "$http_code" = "433" ]; then
        echo "[RATE LIMITED] Hourly credit limit exceeded. Waiting 60s..." >&2
        sleep 60
        call_api "$endpoint" "$data" "$method"
        return $?
    fi

    echo "$body"
}

$QUIET || echo "=== KIE Image ==="
$QUIET || echo "Prompt: $PROMPT"
$QUIET || echo "Model: $MODEL"
$QUIET || echo "Aspect: $ASPECT_RATIO | Quality: $QUALITY"
[ -n "$IMAGE_URL" ] && $QUIET || echo "Input image: $IMAGE_URL"
$QUIET || echo ""

if [ -n "$IMAGE_URL" ]; then
    JSON_DATA=$(cat <<ENDJSON
{
    "model": "$MODEL",
    "input": {
        "prompt": "$PROMPT",
        "image_urls": ["$IMAGE_URL"],
        "aspect_ratio": "$ASPECT_RATIO",
        "quality": "$QUALITY",
        "nsfw_checker": false
    }
}
ENDJSON
)
else
    JSON_DATA=$(cat <<ENDJSON
{
    "model": "$MODEL",
    "input": {
        "prompt": "$PROMPT",
        "aspect_ratio": "$ASPECT_RATIO",
        "quality": "$QUALITY",
        "nsfw_checker": false
    }
}
ENDJSON
)
fi

RESPONSE=$(call_api "/api/v1/jobs/createTask" "$JSON_DATA")

TASK_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('taskId', ''))" 2>/dev/null || echo "")

if [ -z "$TASK_ID" ]; then
    echo "Error: no taskId. Response: $RESPONSE" >&2
    exit 1
fi

$QUIET || echo "Task ID: $TASK_ID"
$QUIET || echo "Polling..."
$QUIET || echo ""

# Image-to-image can take 5+ minutes, so extend timeout
MAX_POLLS=120
if [ -n "$IMAGE_URL" ]; then
    MAX_POLLS=200
fi

for i in $(seq 1 $MAX_POLLS); do
    sleep 5

    RESULT=$(call_api "/api/v1/jobs/recordInfo?taskId=$TASK_ID" "" "GET" 2>/dev/null || echo "")

    if [ -z "$RESULT" ]; then
        echo "Query failed, retrying..."
        continue
    fi

    STATE=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('state', ''))" 2>/dev/null || echo "unknown")

    $QUIET || echo "[$i] State: $STATE"

    if [ "$STATE" = "success" ]; then
        $QUIET || echo ""

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
            SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
            OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/output}"
            mkdir -p "$OUTPUT_DIR"
            TIMESTAMP=$(date +%s%3N)
            while IFS= read -r url; do
                if [ -n "$url" ]; then
                    local_file="$OUTPUT_DIR/kie_${TIMESTAMP}"
                    [ -n "$TAG" ] && local_file="${local_file}_${TAG}"
                    local_file="${local_file}.jpg"
                    $QUIET || echo "Download: $local_file"
                    curl -sS -o "$local_file" "$url"
                    $QUIET || echo "Saved: $(basename "$local_file") ($(stat -c%s "$local_file")B)"
                fi
            done <<< "$IMAGE_URLS"
            $QUIET && echo "$IMAGE_URLS"
        fi

        exit 0
    elif [ "$STATE" = "fail" ] || [ "$STATE" = "failed" ]; then
        echo "Task failed: $RESULT" >&2
        exit 1
    fi
done

echo "Timeout waiting for task $TASK_ID"
exit 1
