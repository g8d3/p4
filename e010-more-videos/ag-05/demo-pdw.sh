#!/bin/bash
# demo-pdw.sh — Automated pdw terminal demo
# Records a virtual display while typing pdw commands into foot via wtype
set -uo pipefail

OUTDIR="output/terminal-pdw"
mkdir -p "$OUTDIR"
LOG="$OUTDIR/interaction-log.json"
RAW="$OUTDIR/ag05-raw.mp4"
FINAL="$OUTDIR/ag05-demo.mp4"

echo '[' > "$LOG"

# === DISPLAY SETUP ===
NEW_DISPLAY="HEADLESS-3"
echo "Using display: $NEW_DISPLAY"

# Open foot on the display (ensure it's there)
../ag-00/bin/pdw w ls 2>/dev/null | grep -q foot || \
    ../ag-00/bin/pdw w new "$NEW_DISPLAY" foot --maximized
sleep 2

# === RECORDING START ===
START_TS=$(date +%s.%N)
echo "Starting wf-recorder on $NEW_DISPLAY for 60s..."
WAYLAND_DISPLAY=wayland-1 wf-recorder -f "$RAW" -o "$NEW_DISPLAY" \
    --no-dmabuf --no-damage -c libx264 -r 25 &
REC_PID=$!
sleep 1

# Helper: log + type a command
type_cmd() {
    local cmd="$1"
    local after="${2:-2}"
    local t=$(echo "$(date +%s.%N) - $START_TS" | bc)
    echo "{\"t\": $t, \"cmd\": \"$cmd\", \"note\": \"typing\"}," >> "$LOG"
    printf "[t=%5.1f] %s\n" "$t" "$cmd"
    sleep 0.3
    WAYLAND_DISPLAY=wayland-1 wtype "$cmd"
    sleep 0.2
    WAYLAND_DISPLAY=wayland-1 wtype -k Return
    sleep "$after"
}

# Clear terminal first
sleep 1
WAYLAND_DISPLAY=wayland-1 wtype "clear"
sleep 0.2
WAYLAND_DISPLAY=wayland-1 wtype -k Return
sleep 1

# === DEMO COMMANDS ===
# Each typed command + wait for output to appear

# 1. Help menu
type_cmd "pdw --help" 3

# 2. Show current state
type_cmd "pdw ls" 4

# 3. Create a new virtual display
type_cmd "pdw ds new" 3

# 4. List displays
type_cmd "pdw ds ls" 3

# 5. Open a terminal on an existing display
type_cmd "pdw w new HEADLESS-4 foot --maximized" 4

# 6. List windows
type_cmd "pdw w ls" 3

# 7. Record a display
type_cmd "pdw rec HEADLESS-4 5" 4

# 8. VNC
type_cmd "pdw vnc new HEADLESS-3" 3

# 9. List VNC
type_cmd "pdw vnc ls" 3

# 10. Cleanup
type_cmd "pdw clean" 3

# === FINISH ===
sleep 2

# Close JSON properly
sed -i '$ s/,$//' "$LOG"
echo ']' >> "$LOG"

# Stop recording
kill "$REC_PID" 2>/dev/null
wait 2>/dev/null
echo "Recording stopped"

# === ENCODE ===
echo "Encoding with VAAPI..."
ffmpeg -y -i "$RAW" -vaapi_device /dev/dri/renderD128 \
    -vf "format=nv12,hwupload" -c:v h264_vaapi -b:v 2M "$FINAL" 2>/dev/null || cp "$RAW" "$FINAL"

rm -f "$RAW"

# === METADATA ===
D=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$FINAL" 2>/dev/null || echo "45")
FS=$(stat -c%s "$FINAL" 2>/dev/null || echo 0)
META="$OUTDIR/ag05-demo.metadata.json"
cat > "$META" << EOF
{
  "duration_sec": $D,
  "file_size": $FS,
  "output": "$NEW_DISPLAY",
  "resolution": "608x1080"
}
EOF

echo "=== Done ==="
echo "Video: $(ls -lh "$FINAL" | awk '{print $5}')"
echo "Log: $(wc -c < "$LOG") bytes"
