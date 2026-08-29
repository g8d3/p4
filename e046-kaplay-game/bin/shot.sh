#!/usr/bin/env bash
# shot.sh — screenshot the game with agent-browser, then ALWAYS close it.
#
# Why: the user asked that the browser (a) use GPU where possible and (b) be
# closed when no longer needed. Agent-browser's headless Chromium renders via
# SwiftShader (software) and cannot reliably use the AMD Radeon GPU; the only
# real control we have is to keep the session short and clean up after.
#
# It retries the screenshot because headless WebGL sometimes needs a moment to
# paint the first frame. On success it closes the browser in all paths (trap).
#
# Usage:
#   bin/shot.sh [output.png] [url] [press_space 0|1]
set -euo pipefail

OUT="${1:-/tmp/e046-shot.png}"
URL="${2:-http://localhost:5173/}"
PRESS="${3:-1}"

cleanup() {
    agent-browser close --all >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

echo "→ opening ${URL}"
agent-browser open "${URL}" >/dev/null 2>&1
sleep 4   # let Vite + Kaplay load and draw the WebGL canvas

if [ "${PRESS}" = "1" ]; then
    agent-browser press " " >/dev/null 2>&1 || true
    sleep 2
fi

# Retry until the canvas is not blank (blank canvas → tiny/empty screenshot).
ok=""
for i in 1 2 3 4 5; do
    agent-browser screenshot "#game" "${OUT}" >/dev/null 2>&1 || true
    size=$(stat -c%s "${OUT}" 2>/dev/null || echo 0)
    # A rendered 480x270 canvas yields a multi-KB PNG; ~4000 or less is blank.
    if [ "${size}" -gt 8000 ]; then ok="1"; break; fi
    echo "  (attempt ${i}: ${size} bytes — retrying)"
    agent-browser press " " >/dev/null 2>&1 || true
    sleep 2
done

if [ -n "${ok}" ]; then
    echo "✓ saved ${OUT} (${size} bytes)"
else
    echo "⚠ screenshot may be blank (${size} bytes); press space/capture in desktop browser"
fi

echo "→ closing browser"
cleanup
echo "✓ done"
