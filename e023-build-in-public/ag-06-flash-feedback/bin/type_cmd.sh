#!/usr/bin/env bash
# Reliable wtype typing for headless sway: type a command, verify the text
# landed on screen (OCR), retry until correct, then optionally press Return.
# Usage: type_cmd.sh <expected_fragment> [--enter]
export SWAYSOCK=/run/user/1000/sway-ipc.1000.240699.sock
export WAYLAND_DISPLAY=wayland-1
FRAG="$1"
ENTER=0
[ "$2" = "--enter" ] && ENTER=1
TMP=/tmp/typecheck.png
for attempt in 1 2 3 4 5; do
  printf '%s\n' "$FRAG" | wtype -d 80 -
  sleep 1.2
  grim -o HEADLESS-4 "$TMP"
  if tesseract "$TMP" - 2>/dev/null | grep -q "$FRAG"; then
    echo "TYPED_OK attempt=$attempt"
    if [ "$ENTER" = 1 ]; then
      sleep 0.4
      wtype -k Return
      sleep 2.5
    fi
    exit 0
  fi
  echo "retry $attempt (OCR did not find '$FRAG')"
  # clear line so we don't accumulate garbage: Ctrl+U
  wtype -k ctrl+u 2>/dev/null
  sleep 0.8
done
echo "TYPING_FAILED after 5 attempts: $FRAG"
exit 1
