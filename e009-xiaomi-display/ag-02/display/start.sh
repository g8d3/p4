#!/usr/bin/env bash
set -euo pipefail

DISPLAY_NUM="${1:-1}"
RESOLUTION="${2:-720x1600}"
export DISPLAY=":${DISPLAY_NUM}"

Xvfb "${DISPLAY}" -screen 0 "${RESOLUTION}x24" &
sleep 1

openbox &
sleep 1

    nohup x11vnc -display "${DISPLAY}" -forever -nopw -quiet -rfbport $((5900 + DISPLAY_NUM)) >/dev/null 2>&1 &
