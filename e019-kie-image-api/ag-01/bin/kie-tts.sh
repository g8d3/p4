#!/usr/bin/env bash
set -euo pipefail

# KIE TTS API wrapper (ElevenLabs & Gemini)
# Requires: KIE_API_KEY environment variable
#
# Usage:
#   ./kie-tts.sh "<text>" [model] [voice]
#
# Models:
#   elevenlabs/text-to-speech-turbo-2-5  (default, 6.0 credits)
#   elevenlabs/text-to-speech-multilingual-v2
#   elevenlabs/text-to-dialogue-v3
#   google/gemini-3-1-flash-tts            (0.42 credits, multi-speaker)
#   google/gemini-2-5-pro-tts
#
# Examples:
#   ./kie-tts.sh "Hello world"
#   ./kie-tts.sh "Hello world" elevenlabs/text-to-speech-turbo-2-5
#   ./kie-tts.sh "Hello world" google/gemini-3-1-flash-tts

API_BASE="${KIE_API_BASE_URL:-https://api.kie.ai}"
TEXT="${1:?Usage: kie-tts.sh <text> [model] [voice]}"
MODEL="${2:-elevenlabs/text-to-speech-turbo-2-5}"
VOICE="${3:-}"

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/output}"

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

build_payload() {
    case "$MODEL" in
        elevenlabs/*)
            local voice_arg
            if [ -n "$VOICE" ]; then
                voice_arg="$VOICE"
            else
                voice_arg="N2lVS1w4EtoT3dr4eOWO"
            fi
            cat <<ENDJSON
{
    "model": "$MODEL",
    "input": {
        "text": "$TEXT",
        "voice": "$voice_arg",
        "stability": 0.5,
        "similarity_boost": 0.75
    }
}
ENDJSON
            ;;
        google/*)
            cat <<ENDJSON
{
    "model": "$MODEL",
    "input": {
        "temperature": 1,
        "scene": "",
        "speakers": [
            {
                "speaker_id": "Speaker 1",
                "voice_name": "${VOICE:-Fenrir}",
                "audio_profile": "Narrator",
                "accent": "American (Gen)",
                "pace": "Natural"
            }
        ],
        "dialogue_turns": [
            {
                "speaker_id": "Speaker 1",
                "text": "$TEXT"
            }
        ]
    }
}
ENDJSON
            ;;
        *)
            echo "Unknown model: $MODEL" >&2
            exit 1
            ;;
    esac
}

echo "=== Creating TTS task ==="
echo "Model: $MODEL"
echo "Text: $TEXT"
echo ""

JSON_DATA=$(build_payload)
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

        AUDIO_URLS=$(echo "$RESULT" | python3 -c "
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

        if [ -n "$AUDIO_URLS" ]; then
            echo ""
            echo "Audio URLs:"
            echo "$AUDIO_URLS"
            echo ""

            mkdir -p "$OUTPUT_DIR"
            TIMESTAMP=$(date +%s)
            while IFS= read -r url; do
                if [ -n "$url" ]; then
                    local_file="$OUTPUT_DIR/kie-tts_${TIMESTAMP}"
                    echo "Downloading: $url"
                    curl -sS -o "${local_file}.wav" "$url"

                    echo "Converting to MP3..."
                    ffmpeg -y -i "${local_file}.wav" -codec:a libmp3lame -qscale:a 2 "${local_file}.mp3" 2>/dev/null
                    echo "Saved: ${local_file}.mp3"
                fi
            done <<< "$AUDIO_URLS"
        fi

        exit 0
    elif [ "$STATE" = "fail" ] || [ "$STATE" = "failed" ]; then
        echo ""
        echo "=== Task failed ==="
        echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"
        exit 1
    fi
done

echo "Timeout waiting for task $TASK_ID"
exit 1
