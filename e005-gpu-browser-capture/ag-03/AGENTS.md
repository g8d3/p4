# ag-03 — Autonomous content recording agent

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, GPU encoding, tmux naming, commit rules
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../SETUP.md](../SETUP.md) — recording pipeline

## Goal

Record yourself autonomously exploring AI/open-source topics. Produce a **single** vertical (608×1080) video with GPU-accelerated encoding, **merged audio+narration**, and web-optimized seeking. Narrate your actions and decisions in real-time using edge-tts.

You are an autonomous content creator. **You decide**:
- Duration (10s-60s, whatever fits the content)
- What to do (browse, code, read, compare, demo)
- How to make it visually interesting (scroll, click, type, navigate)
- Your narration style (educational, entertaining, exploratory)

Think about what makes an engaging short video. A 20s screen recording of static text is boring. A 20s demo of scrolling through trending AI repos with commentary is interesting. Be creative.

## Critical: Browser must render visible MOTION

Xvfb shows a blank screen by default. You must **interact** with the browser to create visible motion on screen. Static pages look like a screenshot.

**Good motion sources** (pick at least two):
1. **Scroll**: `xdotool key Down` repeatedly to scroll a long page
2. **Type**: `xdotool type "text"` to type in a search box or text field
3. **Navigate**: Open multiple tabs (`Ctrl+T` via xdotool), switch between them
4. **Video**: Open a YouTube/social media short (auto-plays, gives motion)
5. **Animations**: Load a page with CSS/JS animations (huggingface spaces, three.js demos)
6. **Click**: `xdotool click 1` to click on links or buttons

**Sequence for a 30-second video**:
```
0-5s:   Open browser, load page, narrate intent
5-15s:  Scroll through content (xdotool key Down every 2s)
15-20s: Click a link, load new page
20-28s: Read/scrolling new page
28-30s: Narration wraps up
```

## Display setup

You get your own Xvfb virtual display:

```bash
Xvfb :99 -screen 0 608x1080x24 &>/dev/null &
sleep 1
export DISPLAY=:99
```

Your display is 608×1080 vertical (TikTok/Reels format).

## Pipeline

```
1. Start Xvfb :99 (virtual display)
2. Launch browser, load a visual page, verify with screenshot
3. Start resource monitor (GPU/CPU/disk → resources.csv)
4. Start edge-tts narration → narration.mp3
5. Begin ffmpeg recording (x11grab + VAAPI) → raw_video.mp4
6. INTERACT with browser: scroll, click, type, navigate (duration you decide)
7. Stop recording, stop narration
8. Merge audio + video → capture.mp4 (with -movflags +faststart)
9. Log pipeline metrics to runs.csv
10. Verify the video
11. Delete intermediate files
```

## Tools available

- **Browser**: `google-chrome --no-sandbox --disable-gpu --window-size=608,1080 --new-window "URL"`
  - `--disable-gpu` is required for Xvfb (no GPU acceleration in virtual display)
  - Verify it's running: `pgrep chrome`
  - Screenshot to confirm: `import -window root /tmp/screen.png && file /tmp/screen.png`
- **Keyboard/mouse automation** (xdotool):
  ```bash
  # Scroll down
  xdotool key Down
  xdotool key Page_Down
  # Type text
  xdotool type "text to type"
  # Click at position
  xdotool mousemove 300 540 click 1
  # Open new tab
  xdotool key ctrl+t
  # Switch tab
  xdotool key ctrl+Tab
  ```
- **Recording**: `ffmpeg -vaapi_device /dev/dri/renderD128 -f x11grab -video_size 608x1080 -i :99.0 -t 30 -vf "format=nv12,hwupload" -c:v h264_vaapi -b:v 4M -y raw_video.mp4`
- **Narration**: `edge-tts --voice es-CO-GonzaloNeural --text "..." --write-media narration.mp3`
- **Merge**:
  ```bash
  ffmpeg -i raw_video.mp4 -i narration.mp3 -c:v copy -c:a aac -b:a 128k -movflags +faststart -shortest -y capture.mp4
  ```
- **AI topics to explore**: github.com/trending, huggingface.co/models, huggingface.co/spaces, new model releases, AI frameworks, agent systems, memory architectures, RAG, fine-tuning, etc.

## Resource monitor (resources.csv)

Run this in background during recording to log per-second resource usage:

```bash
MON_CSV="resources.csv"
echo "timestamp,gpu_busy_pct,cpu_pct,disk_write_kbps,memory_mb" > "$MON_CSV"
# Run loop in background
(
  while true; do
    TS=$(date -Iseconds)
    GPU=$(cat /sys/class/drm/card2/device/gpu_busy_percent 2>/dev/null || echo 0)
    CPU=$(ps -p $BROWSER_PID -o %cpu= 2>/dev/null || echo 0)
    DISK=$(cat /sys/block/$(df --output=source . | tail -1 | sed 's/\/dev\///')/stat 2>/dev/null | awk '{print $7*512/1024}' || echo 0)
    echo "$TS,$GPU,$CPU,0,$DISK" >> "$MON_CSV"
    sleep 1
  done
) &
MON_PID=$!
```

## Pipeline metrics (runs.csv)

Every run appends to `runs.csv` (cumulative log of all recording runs):

```bash
if [ ! -f runs.csv ]; then
  echo "timestamp,run_id,experiment,agent_id,step,tool,action,display_type,display_id,gpu_device,gpu_busy_pct,duration_sec,status,notes" > runs.csv
fi

# Log after each step:
STEP_NAME="xvfb"
echo "$(date -Iseconds),$RUN_ID,e005,ag-03,1,xvfb,start,virtual,:99,$GPU,$DURATION,ok,608x1080" >> runs.csv
```

Required steps to log: xvfb, browser, narration, recording, merge, verify.

## Files

- `capture.mp4` — final merged video
- `raw_video.mp4` — video-only (delete after merge)
- `narration.mp3` — audio (delete after merge)
- `findings.md` — what you learned
- `resources.csv` — per-second resource telemetry (GPU, CPU, disk)
- `runs.csv` — cumulative pipeline log: one row per run, appended each execution

## Interaction sequence

When recording starts, execute this loop:

```bash
# Inside the 30s recording window, every 2 seconds do something:
for i in $(seq 1 10); do
  case $i in
    1) xdotool key Down ;;    # scroll
    2) sleep 1 ;;
    3) xdotool key Down ;;
    4) sleep 1 ;;
    5) xdotool key ctrl+Tab ;; # switch tab
    6) sleep 1 ;;
    7) xdotool key Down ;;
    8) xdotool key Down ;;
    9) xdotool key Down ;;
   10) sleep 1 ;;
  esac
  sleep 2
done
```

## Verification

After merge, check:
- `stat capture.mp4` — file exists and size > 1 MB
- Resolution: `ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 capture.mp4`
- Has audio: `ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 capture.mp4`
- Not corrupt: `ffprobe -v error capture.mp4`
- Clean up: `rm -f raw_video.mp4 narration.mp3`

## Self-command

All commands in background. Self-wake after each step.

```bash
(sleep <N>; tmux send-keys -t 5-3 "Self-wake: <context: which step, what to check, what to do next>" Enter) &
```
