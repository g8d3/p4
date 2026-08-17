#!/bin/bash
# vision-check.sh <image> [prompt] — ask mimo-v2.5 to describe a screenshot
set -u
IMG="$1"
PROMPT="${2:-Describe this screenshot in 2-4 short sentences. Is a 3D character visible? What colors? Any text?}"
cd "$(dirname "$0")"
timeout 120 opencode run -m opencode-go/mimo-v2.5 "You are an image analyzer. Describe the image at $IMG in 3-5 short sentences. $PROMPT" 2>&1 | tail -30