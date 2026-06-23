#!/bin/bash
# record.sh — manage virtual displays and record them
set -uo pipefail

CMD="${1:-help}"; shift 2>/dev/null || true
OUTDIR="$(dirname "$0")/../output"; mkdir -p "$OUTDIR"
SWAY_CONF="$(dirname "$0")/sway-headless.conf"
WLDISPLAY="wayland-1"

sock() { ls -t /run/user/$(id -u)/sway-ipc.*.sock 2>/dev/null | head -1; }
sway_pid() { local s=$(sock); [ -n "$s" ] && echo "$s" | grep -oP '\d+(?=\.sock$)'; }
sway_alive() {
    local p=$(sway_pid)
    [ -n "$p" ] || return 1
    kill -0 "$p" 2>/dev/null || return 1
    [ -e "/run/user/$(id -u)/$WLDISPLAY" ] || return 1
    swaymsg -t get_outputs >/dev/null 2>&1
}
swaymsg() { SWAYSOCK=$(sock) command swaymsg "$@" 2>/dev/null; }
app_on_output() { swaymsg -t get_tree 2>/dev/null | python3 -c "
import sys,json
t=json.load(sys.stdin)
def find(n,d=0):
    a=n.get('app_id','') or ''
    o=n.get('output','') or ''
    if a: print(f'{a} on {o}')
    for c in n.get('nodes',[])+n.get('floating_nodes',[]): find(c,d+1)
find(t)
" 2>/dev/null; }
list_outputs() { swaymsg -t get_outputs 2>/dev/null | grep -oP '"name":"\K[^"]+'; }
list_windows() { swaymsg -t get_tree 2>/dev/null | python3 -c "
import sys,json
def show(n,d=0):
    t=n.get('type','')
    a=n.get('app_id','') or ''
    o=n.get('output','') or ''
    if (t=='con' and a) or (t=='output' and o):
        print(f\"{'  '*d}{t}:{a or o}\")
    for c in n.get('nodes',[])+n.get('floating_nodes',[]): show(c,d+1)
show(json.load(sys.stdin))
" 2>/dev/null; }

# === status ===
if [ "$CMD" = "status" ]; then
    if ! sway_alive; then echo "Sway: NOT running"; exit 0; fi
    echo "Sway: running"
    echo "Outputs:"; list_outputs | sed 's/^/  /'
    echo "Windows:"; list_windows | sed 's/^/  /'
    exit 0
fi

# === start ===
if [ "$CMD" = "start" ]; then
    if sway_alive; then echo "Sway already running"; exit 0; fi
    # Kill stale sway processes (not the real desktop sway)
    pgrep -f "sway.*$SWAY_CONF" 2>/dev/null | while read p; do kill "$p" 2>/dev/null; done
    sleep 1
    echo "Starting Sway..."
    WLR_BACKENDS=headless WLR_RENDERER=vulkan WLR_LIBINPUT_NO_DEVICES=1 \
        sway --config "$SWAY_CONF" >/dev/null 2>&1 &
    sleep 2
    sway_alive && echo "Ready" || { echo "Failed"; exit 1; }
    exit 0
fi

# === create ===
if [ "$CMD" = "create" ]; then
    sway_alive || { echo "Start sway first"; exit 1; }
    OUTPUT="${1:-HEADLESS-$(($(list_outputs | wc -l) + 1))}"
    swaymsg create_output >/dev/null 2>&1
    sleep 1
    echo "Created $(list_outputs | tail -1)"
    exit 0
fi

# === open ===
if [ "$CMD" = "open" ]; then
    OUTPUT="${1:?usage: record.sh open <output> <command>}"
    shift
    sway_alive || { echo "Start sway first"; exit 1; }
    echo "Opening $* on $OUTPUT..."
    swaymsg "workspace $(echo "$OUTPUT" | tr -cd A-Z0-9-)" >/dev/null 2>&1
    WAYLAND_DISPLAY="$WLDISPLAY" "$@" &
    sleep 3
    # Verify it appeared
    list_windows | grep -q "$OUTPUT" && echo "Verified on $OUTPUT" || echo "WARNING: not visible on $OUTPUT"
    exit 0
fi

# === record ===
if [ "$CMD" = "record" ]; then
    NAME="${1:?usage: record.sh record <name> <output> [sec]}"
    OUTPUT="${2:?usage: record.sh record <name> <output> [sec]}"
    DURATION="${3:-60}"
    RAW="$OUTDIR/${NAME}_raw.mp4"; FINAL="$OUTDIR/${NAME}.mp4"
    META="$OUTDIR/${NAME}.metadata.json"
    sway_alive || { echo "Start sway first"; exit 1; }
    # Create output if needed
    list_outputs | grep -qx "$OUTPUT" || { echo "Creating $OUTPUT..."; swaymsg create_output >/dev/null 2>&1; sleep 1; }
    echo "Recording $OUTPUT for ${DURATION}s..."
    START_TS=$(date -Iseconds)
    WAYLAND_DISPLAY="$WLDISPLAY" wf-recorder -f "$RAW" -o "$OUTPUT" \
        --no-dmabuf --no-damage -c libx264 -r 25 &
    REC_PID=$!; sleep "$DURATION"; kill "$REC_PID" 2>/dev/null || true; wait 2>/dev/null || true
    END_TS=$(date -Iseconds)
    echo "Encoding..."
    ffmpeg -y -i "$RAW" -vaapi_device /dev/dri/renderD128 \
        -vf "format=nv12,hwupload" -c:v h264_vaapi -b:v 2M "$FINAL" 2>/dev/null || cp "$RAW" "$FINAL"
    DUR_SEC=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$FINAL" 2>/dev/null || echo "$DURATION")
    cat > "$META" << EOF
{"duration_sec": $DUR_SEC, "output": "$OUTPUT",
 "file_size": $(stat -c%s "$FINAL" 2>/dev/null || echo 0),
 "recording_start": "$START_TS", "recording_end": "$END_TS"}
EOF
    rm -f "$RAW"; echo "Done: $(ls -lh "$FINAL" | awk '{print $5, $NF}')"
    exit 0
fi

# === demo ===
if [ "$CMD" = "demo" ]; then
    # Full workflow: start → create outputs → open apps → record
    OUT1="${1:-HEADLESS-1}"; OUT2="${2:-HEADLESS-2}"; SEC="${3:-10}"
    echo "=== Demo: 2 displays, ${SEC}s each ==="
    # Read state
    echo "--- System state ---"
    bash "$0" status
    echo "---"
    # Start sway
    bash "$0" start || exit 1
    # Create outputs (skip if exist)
    list_outputs | grep -qx "$OUT1" || bash "$0" create
    list_outputs | grep -qx "$OUT2" || bash "$0" create
    # Open apps
    bash "$0" open "$OUT1" foot --maximized &
    sleep 2
    bash "$0" open "$OUT2" google-chrome --ozone-platform=wayland \
        --profile-directory=Default --user-data-dir=$HOME/profiles/chrome-main \
        --new-window https://x.com/bookmarks &
    sleep 5
    # Verify
    echo "--- Verify ---"
    bash "$0" status
    echo "--- Recording ---"
    bash "$0" record demo1 "$OUT1" "$SEC" &
    R1=$!
    bash "$0" record demo2 "$OUT2" "$SEC" &
    R2=$!
    wait $R1 $R2 2>/dev/null
    echo "=== Demo done ==="
    ls -lh "$OUTDIR"/demo*.mp4
    exit 0
fi

# === help ===
echo "Usage: record.sh <command> [args]
  start                  start sway headless
  status                 show current state (outputs, windows)
  create [name]          create a new virtual output
  open <out> <cmd..>     open app on output (verifies it appears)
  record <name> <out> [sec]  record an output
  demo [out1] [out2] [sec]   full demo: start → create → open → record

Examples:
  record.sh status
  record.sh start
  record.sh create HEADLESS-2
  record.sh open HEADLESS-1 foot --maximized
  record.sh record demo HEADLESS-1 30
  record.sh demo HEADLESS-1 HEADLESS-2 10"
