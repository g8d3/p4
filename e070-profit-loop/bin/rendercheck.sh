#!/bin/bash
# Human-like render check, local only ($0). Opens the desk in a real browser
# with JS executed and reads VISIBLE text — what curl can never see.
# Fails on: unfilled ${...} templates, undefined/NaN/$$, missing sections.
# GPU/CPU watch: records the WebGL renderer; fails ONLY on hardware->software
# regression (headless servers correctly report SwiftShader/CPU — not an error).
# Usage: bin/rendercheck.sh [base_url, default http://127.0.0.1:8327]
set -u
BASE="${1:-http://127.0.0.1:8327}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
SESS="e070rc"
BASELINE="$DIR/data/gpu-baseline.txt"

timeout 60 agent-browser --session "$SESS" open "$BASE/" > /dev/null 2>&1 || {
  echo "RENDERCHECK FAIL: browser could not open $BASE"; exit 1; }
sleep 4  # let the page JS fetch /api/state and render, like a human waits
grab() { timeout 90 agent-browser --session "$SESS" eval "$1" 2>/dev/null | python3 -c "import json,sys; s=sys.stdin.read().strip()
try:
    print(json.JSONDecoder().raw_decode(s)[0])
except Exception:
    print('')"; }
TEXT=$(grab "document.body.innerText.slice(0, 12000)")
RENDERER=$(grab "(() => { const c = document.createElement('canvas'); const g = c.getContext('webgl2') || c.getContext('webgl'); if (!g) return 'NO-WEBGL'; const d = g.getExtension('WEBGL_debug_renderer_info'); return d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'WEBGL-NO-INFO'; })()")
timeout 30 agent-browser --session "$SESS" close > /dev/null 2>&1
[ -z "$TEXT" ] && { echo "RENDERCHECK FAIL: empty rendered text"; exit 1; }

FAIL=""
for pat in '${' 'undefined' 'NaN' '$$' 'loading'; do
  case "$TEXT" in *"$pat"*) FAIL="$FAIL artifact:$pat;";; esac
done
for need in 'profit loop' 'funds' 'workers' 'ledger'; do
  case "$TEXT" in *"$need"*|*"${need^}"*) ;; *) FAIL="$FAIL missing:$need;";; esac
done
case "$TEXT" in *'left (floor $'*) ;; *) FAIL="$FAIL prices-unfilled;";; esac

HARDWARE_NOW=$(printf '%s' "$RENDERER" | grep -ciE 'nvidia|amd|radeon|intel|iris|adreno|apple|mali' || true)
if [ ! -s "$BASELINE" ]; then
  printf '%s' "$RENDERER" > "$BASELINE"
  echo "(baseline renderer recorded: $RENDERER)"
else
  OLD=$(cat "$BASELINE")
  HARDWARE_OLD=$(printf '%s' "$OLD" | grep -ciE 'nvidia|amd|radeon|intel|iris|adreno|apple|mali' || true)
  if [ "$HARDWARE_OLD" -gt 0 ] && [ "$HARDWARE_NOW" -eq 0 ]; then
    FAIL="${FAIL}GPU-REGRESSION: was [$OLD], now [$RENDERER];"
  fi
fi

if [ -n "$FAIL" ]; then echo "RENDERCHECK FAIL: $FAIL"; exit 1; fi
echo "RENDERCHECK OK (renderer: $RENDERER)"
