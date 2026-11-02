#!/bin/sh
# Fetch the pinned upstream prototype (gitignored `upstream/` dir).
set -e
HERE=$(dirname "$0")
DEST="$HERE/../upstream"
URL="https://github.com/deepseek-ai/dsh-superagent-prototype"
PIN="6337fc823ce20251c8de8085948165c81aaa701e"
if [ -d "$DEST/.git" ]; then
  git -C "$DEST" fetch --depth 1 origin "$PIN" 2>/dev/null || git -C "$DEST" fetch origin
  git -C "$DEST" checkout --detach "$PIN"
else
  rm -rf "$DEST"
  git clone "$URL" "$DEST"
  git -C "$DEST" checkout --detach "$PIN"
fi
echo "upstream ready at $DEST ($PIN)"
