#!/usr/bin/env bash
set -euo pipefail

# e005 ag-01: GPU-stressed browser recording (Sway + wf-recorder VAAPI)
# Run this from the ag-01 directory

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

OUTPUT_VIDEO="capture.mp4"
METRICS_CSV="metrics.csv"
PIPELINE_LOG="pipeline-log.csv"
LOG_FILE="run.log"
TMPFS_DIR="/dev/shm/e005-capture"

RUN_ID="run-$(date +%Y%m%d-%H%M%S)"
EXPERIMENT="e005"
AGENT_ID="ag-01"

mkdir -p "$TMPFS_DIR"

echo "=== e005 GPU Browser Capture ===" | tee "$LOG_FILE"
echo "Run ID: $RUN_ID" | tee -a "$LOG_FILE"
echo "Started: $(date -Iseconds)" | tee -a "$LOG_FILE"

# Pipeline log header
if [ ! -f "$PIPELINE_LOG" ]; then
  echo "timestamp,run_id,experiment,agent_id,step,tool,action,display_type,display_id,gpu_device,gpu_busy_pct,duration_sec,status,notes" > "$PIPELINE_LOG"
fi

log_step() {
  local step="$1" tool="$2" action="$3" status="$4" notes="$5"
  local ts end_ts dur gpu display_type display_id gpu_device
  end_ts=$(date -Iseconds)
  dur=$(( $(date +%s) - STEP_START ))
  gpu=$(cat /sys/class/drm/card1/device/gpu_busy_percent 2>/dev/null || echo 0)
  display_type="wayland"
  display_id="$WAYLAND_DISPLAY"
  gpu_device="/dev/dri/card1"
  echo "$end_ts,$RUN_ID,$EXPERIMENT,$AGENT_ID,$step,$tool,$action,$display_type,$display_id,$gpu_device,$gpu,$dur,$status,$notes" >> "$PIPELINE_LOG"
}

cleanup() {
  echo "=== Cleaning up ===" | tee -a "$LOG_FILE"
  sudo kill $REC_PID $MON_PID $BROWSER_PID $HTTP_PID $VKCUBE_PID 2>/dev/null || true
  kill $SWAY_SU_PID 2>/dev/null || true
  sleep 0.5
  log_step "cleanup" "kill" "stop all processes" "done" "killed sway, recorder, browser, monitor"
}
trap cleanup EXIT

# ---- Step 1: Start Sway via sudo (on real GPU) ----
echo "=== Step 1/6: Starting Sway compositor ===" | tee -a "$LOG_FILE"
STEP_START=$(date +%s)

mkdir -p "$TMPFS_DIR/runtime"
chmod 0700 "$TMPFS_DIR/runtime"

cat > "$TMPFS_DIR/sway-config" << CFG
set \$mod Mod4
output * bg #111111 solid_color
seat seat0 xcursor_theme default 24
CFG

tmux new-window -n su5 -d
tmux send-keys -t su5 "sudo WLR_DRM_DEVICES=/dev/dri/card1 XDG_RUNTIME_DIR=$TMPFS_DIR/runtime sway -c $TMPFS_DIR/sway-config > $TMPFS_DIR/sway.log 2>&1 &" Enter
sleep 3

if [ -S "$TMPFS_DIR/runtime/wayland-1" ]; then
  sudo chmod 0777 "$TMPFS_DIR/runtime/wayland-1"
  log_step 1 sway compositor "ok" "Sway running on card1, HDMI-A-1"
  echo "Sway running, socket ready" | tee -a "$LOG_FILE"
else
  log_step 1 sway compositor "fail" "socket not found"
  echo "ERROR: Sway socket not found" | tee -a "$LOG_FILE"
  exit 1
fi

export XDG_RUNTIME_DIR="$TMPFS_DIR/runtime"
export WAYLAND_DISPLAY="wayland-1"
export DISPLAY=":0"

# ---- Step 2: Start resource monitor ----
echo "=== Step 2/6: Starting resource monitor ===" | tee -a "$LOG_FILE"
STEP_START=$(date +%s)

sudo XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" WAYLAND_DISPLAY="$WAYLAND_DISPLAY" DISPLAY="$DISPLAY" \
  bash monitor.sh "" "$TMPFS_DIR/$METRICS_CSV" >/dev/null 2>&1 &
MON_PID=$!
sleep 0.5
if kill -0 $MON_PID 2>/dev/null; then
  log_step 2 monitor.sh resource-monitor "ok" "PID=$MON_PID, logging to $METRICS_CSV"
else
  log_step 2 monitor.sh resource-monitor "fail" "monitor failed to start"
fi

# ---- Step 3: Start GPU stress + browser ----
echo "=== Step 3/6: Launching GPU stress and browser ===" | tee -a "$LOG_FILE"
STEP_START=$(date +%s)

python3 -m http.server 8080 --directory "$SCRIPT_DIR" >/dev/null 2>&1 &
HTTP_PID=$!
sleep 0.5

sudo XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" WAYLAND_DISPLAY="$WAYLAND_DISPLAY" DISPLAY="$DISPLAY" \
  vkcube --c 1000000 >/dev/null 2>&1 &
VKCUBE_PID=$!
log_step 3a vkcube vulkan-stress "ok" "PID=$VKCUBE_PID, Vulkan GPU compute load"
echo "vkcube PID=$VKCUBE_PID" | tee -a "$LOG_FILE"

sudo XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" WAYLAND_DISPLAY="$WAYLAND_DISPLAY" DISPLAY="$DISPLAY" \
  epiphany "http://localhost:8080/webgl-stress.html" >/dev/null 2>&1 &
BROWSER_PID=$!
log_step 3b epiphany webgl-browser "ok" "PID=$BROWSER_PID, WebGL stress page"
echo "Browser PID=$BROWSER_PID" | tee -a "$LOG_FILE"

sleep 3

# ---- Step 4: Record 10 seconds (wf-recorder VAAPI) ----
echo "=== Step 4/6: Recording 10 seconds (wf-recorder VAAPI) ===" | tee -a "$LOG_FILE"
STEP_START=$(date +%s)

sudo XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" WAYLAND_DISPLAY="$WAYLAND_DISPLAY" DISPLAY="$DISPLAY" \
  wf-recorder -f "$TMPFS_DIR/capture_raw.mp4" \
    -c h264_vaapi -b 4M \
    --geometry "0,0 608x1080" \
    >/dev/null 2>&1 &
REC_PID=$!
echo "Recorder PID=$REC_PID" | tee -a "$LOG_FILE"

for i in $(seq 10 -1 1); do
  echo "  Recording: ${i}s remaining..." | tee -a "$LOG_FILE"
  sleep 1
done

sudo kill $REC_PID 2>/dev/null || true
sleep 0.5

REC_DURATION=$(( $(date +%s) - STEP_START ))
log_step 4 wf-recorder screen-capture "ok" "PID=$REC_PID, h264_vaapi, 608x1080, ${REC_DURATION}s"
echo "Recording stopped (${REC_DURATION}s)" | tee -a "$LOG_FILE"

# ---- Step 5: Copy output and final metrics ----
echo "=== Step 5/6: Copying output ===" | tee -a "$LOG_FILE"
STEP_START=$(date +%s)

cp "$TMPFS_DIR/capture_raw.mp4" "$OUTPUT_VIDEO"
cp "$TMPFS_DIR/$METRICS_CSV" "$METRICS_CSV"

FILESIZE=$(stat -c%s "$OUTPUT_VIDEO" 2>/dev/null || echo 0)
FILESIZE_MB=$((FILESIZE/1048576))
GPUPCT=$(cat /sys/class/drm/card1/device/gpu_busy_percent 2>/dev/null || echo 0)

log_step 5 cp copy-output "ok" "video=${FILESIZE_MB}MB, metrics.csv copied from tmpfs"
echo "Video: $OUTPUT_VIDEO (${FILESIZE_MB} MB)" | tee -a "$LOG_FILE"
echo "GPU busy: ${GPUPCT}%" | tee -a "$LOG_FILE"

# ---- Step 6: Metrics summary ----
echo "=== Step 6/6: Metrics Summary ===" | tee -a "$LOG_FILE"
STEP_START=$(date +%s)

if [ -f "$METRICS_CSV" ]; then
  SUMMARY=$(awk -F, 'NR>1 {g+=$2; c+=$3; d+=$4; m+=$5; n++} END {printf "Avg GPU: %.1f%% | Avg CPU: %.1f%% | Avg Disk W: %.0f KB/s | Avg Mem: %.0f MB", g/n, c/n, d/n, m/n}' "$METRICS_CSV")
  echo "$SUMMARY" | tee -a "$LOG_FILE"
  log_step 6 awk metrics-summary "ok" "$SUMMARY"
fi

echo "=== DONE ===" | tee -a "$LOG_FILE"

# Print final pipeline log
echo ""
echo "=== Pipeline Log ==="
cat "$PIPELINE_LOG"
