# ag-01 — TTS research screencast

## Model
`opencode-go/mimo-v2.5` (has vision for self-review)

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, self-wake, background commands
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Goal

Produce a screencast video researching modern TTS on X.com and Hugging Face. Record your screen while you work, narrate afterwards, and publish the video.

## Pipeline

```
1. Record screen while researching TTS (wf-recorder)
2. Watch the recording with Mimo 2.5 (vision)
3. Write narration script based on what you saw
4. Generate TTS narration (edge-tts)
5. Compose final video (ffmpeg VAAPI)
6. Review final video with Mimo 2.5
```

## Task

### Step 1: Start screen recording
```bash
WAYLAND_DISPLAY=wayland-1 timeout 300 wf-recorder \
  -f /home/vuos/code/p4/e004-agent-screencast/ag-01/capture.mp4 \
  -c h264_vaapi -b 4M \
  --geometry "656,0 608x1080" >/dev/null 2>&1 &
REC_PID=$!
(sleep 305; tmux send-keys -t e4a "Self-wake: recording done, PID=$REC_PID. Stop recording and continue." Enter) &
```

### Step 2: Prepare the stage (before recording)
- **Suppress browser dialogs**: `xdg-settings set default-web-browser epiphany.desktop >/dev/null 2>&1`
- Open epiphany once to dismiss any first-run dialogs: `WAYLAND_DISPLAY=wayland-1 epiphany https://example.com &` then close it after 3s
- Arrange workspace: open a terminal (weston-terminal) and position it alongside where the browser will go

### Step 3: Record + Research (DO visible work)
Start wf-recorder. Then for each research topic:

1. **Open a specific URL**: `WAYLAND_DISPLAY=wayland-1 epiphany https://x.com/search?q=best+tts+2026`
2. **Wait for page to load**: `sleep 3`
3. **Type a comment in terminal** (this shows on screen): `echo "Looking at X.com search results for TTS models..." > /dev/tty`
4. **Open another URL** to compare: `WAYLAND_DISPLAY=wayland-1 epiphany https://huggingface.co/models?pipeline_tag=text-to-speech`
5. **Type findings**: `echo "Found: Bark, Coqui XTTS, ElevenLabs. Testing Bark..." > /dev/tty`
6. **Actually test a tool**: `pip install bark 2>&1 | head -5` (show real terminal output)
7. **Show test result**: `echo "Bark generates emotional TTS with laughter/crying" > research-notes.md`

Key: every narration point must have a VISIBLE action on screen (typing, browser loading, terminal output).

### Step 3: Stop recording
```bash
kill $REC_PID 2>/dev/null
# Log metrics
FILESIZE=$(stat -c%s /home/vuos/code/p4/e004-agent-screencast/ag-01/capture.mp4 2>/dev/null || echo 0)
GPUPCT=$(cat /sys/class/drm/card*/device/gpu_busy_percent 2>/dev/null | head -1 || echo 0)
echo "$(date -Iseconds),ag-01,e004,recording,$(($(date +%s)-START_TS)),$GPUPCT,0,$((FILESIZE/1048576)),608x1080,drm,wayland-1,wf-recorder capture" \
  >> /home/vuos/code/p4/e004-agent-screencast/ag-03/render-log.csv
```

### Step 4: Watch and review your own video with Mimo 2.5
Read `capture.mp4` with vision. Check:
- **Is the screen content visible?** Can you see browser windows, terminal text, URLs?
- **Does the visual content match the research?** If you talk about Hugging Face, is it visible?
- **Are there long periods of nothing happening?** (idle terminal, loading)
- **Is the framing correct?** 9:16 vertical, readable text
- Write `narration-script.md` with timestamps for reference
- Write `tts-text.txt` — same as narration but WITHOUT timestamps (pure spoken content). Use `cat narration-script.md | sed 's/\[.*\]//g' > tts-text.txt` to strip timestamps
- If the screen is mostly blank or irrelevant, fix by opening more browser windows before re-recording

### Step 5: Generate TTS narration
```bash
# Strip timestamps before feeding to TTS
cat narration-script.md | sed 's/\[.*\]//g' > tts-text.txt
edge-tts --voice en-US-JennyNeural --text "$(cat tts-text.txt)" \
  --write-media /home/vuos/code/p4/e004-agent-screencast/ag-01/narration.mp3
```

### Step 6: Compose final video
```bash
export LIBVA_DRIVER_NAME=radeonsi
ffmpeg -i capture.mp4 -i narration.mp3 \
  -vf "format=nv12,hwupload" -c:v h264_vaapi -c:a aac \
  -y /home/vuos/code/p4/e004-agent-screencast/ag-01/final.mp4
```

### Step 7: Log final metrics
```bash
FILESIZE=$(stat -c%s /home/vuos/code/p4/e004-agent-screencast/ag-01/final.mp4 2>/dev/null || echo 0)
FPS=$(ffprobe -v error -select_streams v -of default=noprint_wrappers=1:nokey=1 -show_entries stream=r_frame_rate /home/vuos/code/p4/e004-agent-screencast/ag-01/final.mp4 2>/dev/null || echo 0)
echo "$(date -Iseconds),ag-01,e004,compose,$DURATION,$GPUPCT,$FPS,$((FILESIZE/1048576)),608x1080,drm,wayland-1,ffmpeg VAAPI" \
  >> /home/vuos/code/p4/e004-agent-screencast/ag-03/render-log.csv
```

### Step 8: Review final video
Read `final.mp4` with Mimo 2.5. Verify:
- Audio sync
- Visual quality
- Content is interesting
- Fix if needed

## Self-command
ALL commands: `>/dev/null 2>&1 &`. Self-wake after each step. Never run synchronously.
