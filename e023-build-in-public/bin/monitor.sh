#!/bin/bash
# Monitor agent resource usage and catch CPU-encoder misuse.
# Run from the orchestrator: ./bin/monitor.sh
#
# What it checks:
#   1. CPU/GPU load overview (loud machine = CPU encoding problem)
#   2. Running wf-recorder / ffmpeg processes and their encoders
#   3. CPU encoders in the FINAL assembly pipeline (libx264/libx265/mpeg4)
#      are flagged as violations — the only allowed libx264 is wf-recorder capture
#   4. Per-agent tmux windows: which producer, is it using GPU
#   5. Transcribe + worker services health
#
# Exit code 0 = clean, 1 = at least one violation found.

VIOLATIONS=0

echo "=== GPU busy % ==="
GB=$(cat /sys/class/drm/card1/device/gpu_busy_percent 2>/dev/null || echo "n/a")
echo "GPU busy: ${GB}%"
echo

echo "=== Top CPU consumers ==="
ps aux --sort=-%cpu | head -8 | awk '{printf "%-7s %6s %4s  %s\n", $1, $3, $4, substr($0, index($0,$11))}'
echo

echo "=== wf-recorder processes (capture — libx264 here is CORRECT) ==="
WFR=$(pgrep -a wf-recorder 2>/dev/null)
if [ -n "$WFR" ]; then
  echo "$WFR"
else
  echo "none"
fi
echo

echo "=== ffmpeg processes (final encode must be h264_vaapi) ==="
FF=$(pgrep -a ffmpeg 2>/dev/null)
if [ -n "$FF" ]; then
  echo "$FF"
  echo "$FF" | grep -qE -- '-c:v (libx264|libx265|mpeg4|mpeg2video|wmv)' && {
    echo "VIOLATION: CPU video encoder detected in ffmpeg pipeline (final encode must use h264_vaapi)."
    VIOLATIONS=$((VIOLATIONS+1))
  }
else
  echo "none"
fi
echo

echo "=== vaapi encoder available ==="
if [ -e /dev/dri/renderD128 ]; then
  echo "renderD128 present"
else
  echo "VIOLATION: /dev/dri/renderD128 missing — GPU encoding impossible"
  VIOLATIONS=$((VIOLATIONS+1))
fi
echo

echo "=== Producer windows ==="
for w in 23-1 23-2 23-3; do
  # match window whose name starts with the exact label (handles legacy trailing dashes)
  WIN=$(tmux list-windows -a -F '#{window_name}' 2>/dev/null | grep -E "^${w}-?$" | head -1)
  if [ -n "$WIN" ]; then
    TOK=$(tmux capture-pane -t "$WIN" -p 2>/dev/null | grep -oE '[0-9]+\.[0-9]K' | tail -1)
    echo "$w: alive as '$WIN' (tokens: ${TOK:-?})"
  else
    echo "$w: NOT running"
  fi
done
echo

echo "=== Services ==="
curl -s --max-time 2 http://127.0.0.1:9877/health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('transcribe:', d['status'])" 2>/dev/null || echo "transcribe: DOWN"
pgrep -f model_worker.py >/dev/null 2>&1 && echo "asr worker: up" || echo "asr worker: DOWN"
echo

if [ "$VIOLATIONS" -gt 0 ]; then
  echo "RESULT: $VIOLATIONS violation(s) found."
  exit 1
fi
echo "RESULT: clean — no CPU-encoder misuse detected."
