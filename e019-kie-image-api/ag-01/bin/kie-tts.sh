#!/usr/bin/env bash
set -euo pipefail

# KIE TTS API wrapper — Gemini & ElevenLabs
# Requires: KIE_API_KEY
#
# Usage:
#   ./kie-tts.sh [options] "<text>"
#
# Options (Gemini):
#   --voice, -v     Voice name (default: Fenrir). 30 options: Achernar..Zubenelgenubi
#                   PREFERRED (p4 default): Alnilam, Gacrux, Puck, Sulafat,
#                   Umbriel, Vindemiatrix — pick one and stay consistent.
#   --scene, -s     Environment description, e.g. "A quiet library at night"
#   --context, -c   Style/tone prompt, e.g. "Calm and reflective"
#   --style         Emotional style: Vocal Smile, Newscaster, Whisper, Empathetic, Promo/Hype, Deadpan
#   --accent        Accent: Neutral, American (Gen/Valley/South), British (RP/Brixton), Transatlantic, Australian
#   --pace          Pace: Natural, Rapid Fire, The Drift, Staccato
#   --profile       Character description, e.g. "A young engineering student"
#   --model, -m     Model (default: google/gemini-3-1-flash-tts)
#   --quiet, -q     Machine-readable output (MP3 path only)
#   --tag, -t       Output filename tag
#
# Examples:
#   ./kie-tts.sh "Hello world"
#   ./kie-tts.sh --voice Kore --scene "Subway station" --context "Tired and nostalgic" "Diecisiete minutos..."
#   ./kie-tts.sh --voice Iapetus --accent "American (South)" --pace Natural "Howdy partner"

API_BASE="${KIE_API_BASE_URL:-https://api.kie.ai}"
QUIET=false
TAG=""
MODEL="google/gemini-3-1-flash-tts"
VOICE="Fenrir"
SCENE=""
CONTEXT=""
STYLE=""
ACCENT="Neutral"
PACE="Natural"
PROFILE="Narrator"

# Parse args: flags first, then bare text
FLAGS=()
while [ $# -gt 0 ]; do
    case "$1" in
        --quiet|-q) QUIET=true; shift ;;
        --tag|-t) TAG="$2"; shift 2 ;;
        --model|-m) MODEL="$2"; shift 2 ;;
        --voice|-v) VOICE="$2"; shift 2 ;;
        --scene|-s) SCENE="$2"; shift 2 ;;
        --context|-c) CONTEXT="$2"; shift 2 ;;
        --style) STYLE="$2"; shift 2 ;;
        --accent) ACCENT="$2"; shift 2 ;;
        --pace) PACE="$2"; shift 2 ;;
        --profile) PROFILE="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: kie-tts.sh [options] \"<text>\""
            echo "  --voice, -v       Voice name (default: Fenrir)"
            echo "  --scene, -s       Environment description"
            echo "  --context, -c     Style/tone prompt"
            echo "  --style           Vocal Smile, Newscaster, Whisper, Empathetic, Promo/Hype, Deadpan"
            echo "  --accent          Neutral, American (Gen/Valley/South), British (RP/Brixton)..."
            echo "  --pace            Natural, Rapid Fire, The Drift, Staccato"
            echo "  --profile         Character description"
            echo "  --model, -m       Model override"
            echo "  --quiet, -q       Machine-readable output"
            echo "  --tag, -t         Output filename tag"
            exit 0 ;;
        *) TEXT="$1"; shift ;;
    esac
done

: "${TEXT:?Usage: kie-tts.sh [options] \"<text>\"}"

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/output}"

call_api() {
    local endpoint="$1" data="${2:-}" method="${3:-POST}"
    if [ "$method" = "GET" ]; then
        curl -sS "$API_BASE$endpoint" -H "Authorization: Bearer $KIE_API_KEY"
    else
        printf '%s' "$data" | curl -sS "$API_BASE$endpoint" \
            -H "Authorization: Bearer $KIE_API_KEY" \
            -H "Content-Type: application/json" -X "$method" -d @-
    fi
}

# Build JSON payload
if [[ "$MODEL" == elevenlabs/* ]]; then
    JSON_DATA=$(cat <<ENDJSON
{"model":"$MODEL","input":{"text":"$TEXT","voice":"$VOICE","stability":0.5,"similarity_boost":0.75}}
ENDJSON
)
else
    JSON_DATA=$(cat <<ENDJSON
{"model":"$MODEL","input":{"temperature":1,"scene":"$SCENE","sample_context":"$CONTEXT","speakers":[{"speaker_id":"Speaker 1","voice_name":"$VOICE","audio_profile":"$PROFILE","accent":"$ACCENT","style":"$STYLE","pace":"$PACE"}],"dialogue_turns":[{"speaker_id":"Speaker 1","text":"$TEXT"}]}}
ENDJSON
)
fi

$QUIET || echo "=== KIE TTS ==="
$QUIET || echo "Model: $MODEL | Voice: $VOICE | Style: ${STYLE:-none} | Accent: $ACCENT | Pace: $PACE"
$QUIET || echo ""

RESPONSE=$(call_api "/api/v1/jobs/createTask" "$JSON_DATA" 2>/dev/null)
TASK_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('taskId',''))" 2>/dev/null || echo "")

if [ -z "$TASK_ID" ]; then
    echo "Error: no taskId. Response: $RESPONSE" >&2
    exit 1
fi

$QUIET || echo "Task ID: $TASK_ID | Polling..."

for i in $(seq 1 60); do
    sleep 3
    RESULT=$(call_api "/api/v1/jobs/recordInfo?taskId=$TASK_ID" "" "GET" 2>/dev/null || echo "")

    STATE=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('state',''))" 2>/dev/null || echo "unknown")
    $QUIET || echo "[$i] $STATE"

    if [ "$STATE" = "success" ]; then
        AUDIO_URLS=$(echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin).get('data', {})
rj = d.get('resultJson', '{}')
if isinstance(rj, str):
    import json as j2; r = j2.loads(rj)
else: r = rj
for u in r.get('resultUrls', []): print(u)
" 2>/dev/null || echo "")

        if [ -z "$AUDIO_URLS" ]; then
            echo "Error: no audio URL" >&2; exit 1
        fi

        mkdir -p "$OUTPUT_DIR"
        TS=$(date +%s%3N)
        local_file="$OUTPUT_DIR/kie-tts${TAG:+_$TAG}_$TS"

        for url in $AUDIO_URLS; do
            $QUIET || echo "Downloading..."
            curl -sS -o "${local_file}_raw.wav" "$url"
            # Convert directly to MP3, no trimming. The old silenceremove filter
            # stripped natural silence at start/end of every chunk, mutilating the
            # narration (dry cuts, border words clipped). KIE already returns
            # properly-padded audio — convert as-is, then delete the raw WAV.
            ffmpeg -y -i "${local_file}_raw.wav" \
                -codec:a libmp3lame -qscale:a 2 "${local_file}.mp3" 2>/dev/null
            rm -f "${local_file}_raw.wav"
            DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "${local_file}.mp3" 2>/dev/null)
            $QUIET || echo "Saved: $(basename ${local_file}.mp3) (${DUR}s)"
            $QUIET && echo "${local_file}.mp3"
        done
        exit 0
    elif [ "$STATE" = "fail" ]; then
        echo "Task failed: $RESULT" >&2; exit 1
    fi
done

echo "Timeout" >&2; exit 1
