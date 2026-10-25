#!/usr/bin/env bash
# Queue one message for Coco: append a JSON line to coco/inbox_to_coco.jsonl (log)
# and POST the same JSON to the Coco webhook (event, not polling).
# Usage: to_coco.sh "<from>" "<message>"
# ts is the real clock (America/Bogota), never invented.
set -u
FROM="${1:?usage: to_coco.sh <from> <message>}"
MSG="${2:?usage: to_coco.sh <from> <message>}"
DIR="$(cd "$(dirname "$0")/../coco" && pwd)"
ENVF="$(cd "$(dirname "$0")/../.secrets" && pwd)/coco_webhook.env"
# shellcheck disable=SC1090
. "$ENVF"
TS="$(TZ=America/Bogota date '+%Y-%m-%d %H:%M %Z')"
ID="$(date +%s)-$$"
JSON="$(FROM="$FROM" MSG="$MSG" TS="$TS" ID="$ID" python3 -c \
'import json,os; print(json.dumps({"ts":os.environ["TS"],"from":os.environ["FROM"],"msg":os.environ["MSG"],"id":os.environ["ID"]},ensure_ascii=False))')"
printf '%s\n' "$JSON" >> "$DIR/inbox_to_coco.jsonl"
printf '%s' "$JSON" | curl -fsS -m 15 -X POST "$COCO_WEBHOOK_URL" \
  -H "Authorization: Bearer $COCO_WEBHOOK_KEY" \
  -H "Content-Type: application/json" --data @-
CURL_STATUS=$?
echo "queued $ID curl_exit=$CURL_STATUS"
exit "$CURL_STATUS"
