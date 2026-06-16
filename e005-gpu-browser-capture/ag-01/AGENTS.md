# ag-01 — GPU browser recording agent

## Model
`opencode-go/mimo-v2.5` (has vision for self-review)

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, self-wake, sudo windows, background commands
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Goal

Record yourself browsing a WebGL-heavy page for 10 seconds. Maximize GPU utilization, minimize CPU and disk I/O. Monitor and log all resources. Self-review the video.

## Pipeline

```
1. Kill sddm (sudo systemctl stop sddm) → frees DRM master
2. Start Sway as root on card1 (real AMD GPU)
3. Start resource monitor (GPU/CPU/disk → metrics.csv)
4. Launch vkcube (Vulkan GPU stress) + epiphany browser (WebGL)
5. Record 10s with wf-recorder h264_vaapi (GPU encoding)
6. Stop everything, copy output, log metrics
7. Self-review video with Mimo 2.5
8. Suggest improvements
```

## Key design decisions

| Decision | Why |
|----------|-----|
| **Sway + sudo** | Sway needs TTY/logind access. Running as root via sudo on card1 bypasses logind. Real AMD GPU used for all rendering. |
| **wf-recorder h264_vaapi** | Captures wlroots framebuffer → DMA-BUF → VAAPI encode. Zero CPU. Only works with wlroots compositors. |
| **vkcube** | Runs on real GPU via Vulkan, adds parallel GPU compute load independent of display. |
| **epiphany** | GTK WebKit browser with GPU-accelerated WebGL. Runs natively on Wayland. |
| **tmpfs output** | Video written to RAM (/dev/shm). Zero disk I/O for capture. |
| **10 seconds** | Enough for a demo, small file (~5MB). |

## Critical: sudo requirement

Sway runs as root because only root can open `/dev/tty0` from SSH/non-logind sessions. All apps that need the Wayland display (browser, recorder, monitor) must also run via sudo with the same `XDG_RUNTIME_DIR` and `WAYLAND_DISPLAY`.

```bash
sudo XDG_RUNTIME_DIR=/dev/shm/e005-capture/runtime WAYLAND_DISPLAY=wayland-1 DISPLAY=:0 <command>
```

## Files

- `webgl-stress.html` — GPU-burning WebGL2 fragment shader (fullscreen per-pixel 3D noise)
- `monitor.sh` — logs GPU busy%, CPU%, disk write KB/s, memory MB to `metrics.csv` (per-second)
- `run.sh` — full pipeline script
- `pipeline-log.csv` — cumulative pipeline log: one row per step, each run appended (accumulative)

## Task

### Step 0: Read this file and inherited files
Read this AGENTS.md, then read each file in Inherits.

### Step 1: Prepare system (free DRM master)
```bash
RUN_ID="run-$(date +%Y%m%d-%H%M%S)"
echo "RUN_ID=$RUN_ID"

# Create pipeline-log.csv with header if new
if [ ! -f pipeline-log.csv ]; then
  echo "timestamp,run_id,experiment,agent_id,step,tool,action,display_type,display_id,gpu_device,gpu_busy_pct,duration_sec,status,notes" > pipeline-log.csv
fi

tmux new-window -n su5 -d
tmux send-keys -t su5 "sudo systemctl stop sddm" Enter
sleep 3
```

### Step 2: Start Sway
```bash
STEP_START=$(date +%s)

mkdir -p /dev/shm/e005-capture/runtime
chmod 0700 /dev/shm/e005-capture/runtime

cat > /dev/shm/e005-capture/sway-config << 'CFG'
set $mod Mod4
output * bg #111111 solid_color
seat seat0 xcursor_theme default 24
CFG

tmux send-keys -t su5 "sudo WLR_DRM_DEVICES=/dev/dri/card1 XDG_RUNTIME_DIR=/dev/shm/e005-capture/runtime sway -c /dev/shm/e005-capture/sway-config > /dev/shm/e005-capture/sway.log 2>&1 &" Enter
sleep 4

sudo chmod 0777 /dev/shm/e005-capture/runtime/wayland-1

export XDG_RUNTIME_DIR=/dev/shm/e005-capture/runtime
export WAYLAND_DISPLAY=wayland-1
export DISPLAY=:0

DURATION=$(( $(date +%s) - STEP_START ))
GPU=$(cat /sys/class/drm/card1/device/gpu_busy_percent)
echo "$(date -Iseconds),$RUN_ID,e005,ag-01,1,sway,compositor,wayland,wayland-1,/dev/dri/card1,$GPU,$DURATION,ok,Sway on card1 HDMI-A-1" >> pipeline-log.csv
```

### Step 3: Start resource monitor
```bash
STEP_START=$(date +%s)

sudo XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR WAYLAND_DISPLAY=$WAYLAND_DISPLAY DISPLAY=$DISPLAY \
  bash monitor.sh "" /dev/shm/e005-capture/metrics.csv >/dev/null 2>&1 &
MON_PID=$!
sleep 0.5

DURATION=$(( $(date +%s) - STEP_START ))
GPU=$(cat /sys/class/drm/card1/device/gpu_busy_pct)
echo "$(date -Iseconds),$RUN_ID,e005,ag-01,2,monitor.sh,resource-monitor,wayland,wayland-1,/dev/dri/card1,$GPU,$DURATION,ok,PID=$MON_PID" >> pipeline-log.csv
```

### Step 4: Launch GPU stress + browser
```bash
STEP_START=$(date +%s)

python3 -m http.server 8080 --directory . >/dev/null 2>&1 &
HTTP_PID=$!
sleep 0.5

sudo XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR WAYLAND_DISPLAY=$WAYLAND_DISPLAY DISPLAY=$DISPLAY \
  vkcube --c 1000000 >/dev/null 2>&1 &
VKCUBE_PID=$!

sudo XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR WAYLAND_DISPLAY=$WAYLAND_DISPLAY DISPLAY=$DISPLAY \
  epiphany "http://localhost:8080/webgl-stress.html" >/dev/null 2>&1 &
BROWSER_PID=$!

sleep 3

DURATION=$(( $(date +%s) - STEP_START ))
GPU=$(cat /sys/class/drm/card1/device/gpu_busy_pct)
echo "$(date -Iseconds),$RUN_ID,e005,ag-01,4a,vkcube,vulkan-stress,wayland,wayland-1,/dev/dri/card1,$GPU,$DURATION,ok,PID=$VKCUBE_PID" >> pipeline-log.csv
echo "$(date -Iseconds),$RUN_ID,e005,ag-01,4b,epiphany,webgl-browser,wayland,wayland-1,/dev/dri/card1,$GPU,$DURATION,ok,PID=$BROWSER_PID WebGL stress" >> pipeline-log.csv
```

### Step 5: Record 10 seconds
```bash
STEP_START=$(date +%s)

sudo XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR WAYLAND_DISPLAY=$WAYLAND_DISPLAY DISPLAY=$DISPLAY \
  wf-recorder -f /dev/shm/e005-capture/capture_raw.mp4 \
    -c h264_vaapi -b 4M \
    --geometry "0,0 608x1080" >/dev/null 2>&1 &
REC_PID=$!

(sleep 10; tmux send-keys -t 5-1 "Self-wake: 10s done. Kill REC_PID=$REC_PID, finalize." Enter) &
```

### Step 6: Finalize
```bash
STEP_START=$(date +%s)

sudo kill $REC_PID 2>/dev/null; sleep 0.5
cp /dev/shm/e005-capture/capture_raw.mp4 capture.mp4
cp /dev/shm/e005-capture/metrics.csv metrics.csv
sudo kill $MON_PID $BROWSER_PID $VKCUBE_PID $HTTP_PID 2>/dev/null

DURATION=$(( $(date +%s) - STEP_START ))
GPU=$(cat /sys/class/drm/card1/device/gpu_busy_percent)
FILESIZE=$(stat -c%s capture.mp4 2>/dev/null || echo 0)
echo "$(date -Iseconds),$RUN_ID,e005,ag-01,5,wf-recorder,screen-capture,wayland,wayland-1,/dev/dri/card1,$GPU,$DURATION,ok,10s ${FILESIZE}B" >> pipeline-log.csv
echo "$(date -Iseconds),$RUN_ID,e005,ag-01,6,cp,finalize,wayland,wayland-1,/dev/dri/card1,$GPU,$DURATION,ok,video metrics copied" >> pipeline-log.csv

echo "Video: capture.mp4 ($((FILESIZE/1048576)) MB)"
echo "Avg GPU: $(awk -F, 'NR>1 {s+=$2; n++} END {printf \"%.1f%%\", s/n}' metrics.csv 2>/dev/null)"
echo ""
echo "=== Pipeline Log ==="
cat pipeline-log.csv
```

### Step 7: Self-review with Mimo 2.5
Read `capture.mp4` with vision. Check:
- Is the WebGL content rendering? (animated fractal noise colors)
- Is the GPU being utilized? (screen updating smoothly)
- Are there artifacts or black frames?
- Is the 608×1080 vertical framing correct?
- Write findings to `review.md`

### Step 8: Suggest improvements
Write `improvements.md` with:
- What could increase GPU utilization further?
- What could reduce CPU/disk usage?
- Was the sudo requirement a limitation?

### Cleanup
```bash
sudo kill $(pgrep sway) 2>/dev/null
tmux kill-window -t su5 2>/dev/null || true
rm -rf /dev/shm/e005-capture
```

## Self-command

ALL commands: `>/dev/null 2>&1 &`. Self-wake after each step. Never run synchronously.

```bash
(sleep <N>; tmux send-keys -t 5-1 "Self-wake: <context: which step, check what, do what next>" Enter) &
```
