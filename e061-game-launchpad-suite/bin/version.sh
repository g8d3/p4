#!/bin/bash
# e061 version stamp: static demo can't compute live — stamp on every change.
cd "$(dirname "$0")/.." || exit 1
C=$(git log -1 --format=%h -- . 2>/dev/null || echo "?")
D=$(date '+%Y-%m-%d %H:%M')
printf '{"track":"e061","commit":"%s","date":"%s"}' "$C" "$D" > demo/version.json
echo "e061 version.json: $C $D"
