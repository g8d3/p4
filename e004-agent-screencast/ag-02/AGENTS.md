# ag-02 — Visual style research screencast

## Model
`opencode-go/mimo-v2.5` (has vision for self-review)

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, self-wake, background commands
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Goal

Produce a screencast researching video trends, image generation, and visual styles for agent-created videos. Record your screen, narrate, and publish.

## Pipeline

Same as ag-01: record → watch → narrate → compose → review.

## Task

### Step 1: Start recording (vertical 9:16)
```bash
WAYLAND_DISPLAY=wayland-1 timeout 300 wf-recorder \
  -f /home/vuos/code/p4/e004-agent-screencast/ag-02/capture.mp4 \
  -c h264_vaapi -b 4M \
  --geometry "656,0 608x1080" >/dev/null 2>&1 &
REC_PID=$!
START_TS=$(date +%s)
(sleep 305; tmux send-keys -t e4b "Self-wake: recording done." Enter) &
```

### Step 2: Research (while recording)
- **IMPORTANT**: Open browser and navigate to visual examples so the capture shows content
- Open epiphany: `WAYLAND_DISPLAY=wayland-1 epiphany`
- Browse TikTok-style templates, Ken Burns examples, motion graphics
- Search for AI image trends (Flux, SD3, Midjourney) — show the actual pages
- Explore CapCut templates, video transitions
- Type notes in terminal so it's visible in capture
- Take notes in `visual-trends.md`

### Step 3: Stop recording and log
```bash
kill $REC_PID 2>/dev/null
FILESIZE=$(stat -c%s /home/vuos/code/p4/e004-agent-screencast/ag-02/capture.mp4 2>/dev/null || echo 0)
GPUPCT=$(cat /sys/class/drm/card*/device/gpu_busy_percent 2>/dev/null | head -1 || echo 0)
echo "$(date -Iseconds),ag-02,e004,recording,$(($(date +%s)-START_TS)),$GPUPCT,0,$((FILESIZE/1048576)),608x1080,drm,wayland-1,wf-recorder capture" \
  >> /home/vuos/code/p4/e004-agent-screencast/ag-03/render-log.csv
```

### Step 4: Watch and review with Mimo 2.5
Read `capture.mp4` with vision. Check:
- Is the screen content visible? (browser, URLs, examples)
- Does the visual match the research topic?
- Is the 9:16 framing correct?
- Write `narration-script.md` with timestamps for reference
- Write `tts-text.txt` with timestamps stripped: `sed 's/\[.*\]//g' narration-script.md > tts-text.txt`

### Step 5: Generate TTS (English voice)
```bash
cat narration-script.md | sed 's/\[.*\]//g' > tts-text.txt
edge-tts --voice en-US-JennyNeural --text "$(cat tts-text.txt)" \
  --write-media /home/vuos/code/p4/e004-agent-screencast/ag-02/narration.mp3
```

### Step 6: Compose with VAAPI
```bash
export LIBVA_DRIVER_NAME=radeonsi
ffmpeg -i capture.mp4 -i narration.mp3 \
  -vf "format=nv12,hwupload" -c:v h264_vaapi -c:a aac \
  -y /home/vuos/code/p4/e004-agent-screencast/ag-02/final.mp4
```

### Step 7: Log final metrics
```bash
FILESIZE=$(stat -c%s /home/vuos/code/p4/e004-agent-screencast/ag-02/final.mp4 2>/dev/null || echo 0)
FPS=$(ffprobe -v error -select_streams v -of default=noprint_wrappers=1:nokey=1 -show_entries stream=r_frame_rate /home/vuos/code/p4/e004-agent-screencast/ag-02/final.mp4 2>/dev/null || echo 0)
echo "$(date -Iseconds),ag-02,e004,compose,$DURATION,$GPUPCT,$FPS,$((FILESIZE/1048576)),608x1080,drm,wayland-1,ffmpeg VAAPI" \
  >> /home/vuos/code/p4/e004-agent-screencast/ag-03/render-log.csv
```

### Step 8: Review final video with Mimo 2.5
- Audio sync
- Visual quality
- Content matches narration
- Fix if needed

## Self-command
ALL commands: `>/dev/null 2>&1 &`. Self-wake after each step. Never run synchronously.
