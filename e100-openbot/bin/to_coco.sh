#!/usr/bin/env bash
# Append one message for Coco to coco/inbox_to_coco.jsonl as a JSON line.
# Usage: to_coco.sh "<from>" "<message>"
# ts is the real clock (America/Bogota), never invented.
set -u
FROM="${1:?usage: to_coco.sh <from> <message>}"
MSG="${2:?usage: to_coco.sh <from> <message>}"
DIR="$(cd "$(dirname "$0")/../coco" && pwd)"
TS="$(TZ=America/Bogota date '+%Y-%m-%d %H:%M %Z')"
ID="$(date +%s)-$$"
FROM="$FROM" MSG="$MSG" TS="$TS" ID="$ID" python3 -c \
'import json,os; print(json.dumps({"ts":os.environ["TS"],"from":os.environ["FROM"],"msg":os.environ["MSG"],"id":os.environ["ID"]},ensure_ascii=False))' \
>> "$DIR/inbox_to_coco.jsonl"
echo "queued $ID"
