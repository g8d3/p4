# ag-03 — Autonomous content recording agent

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, GPU encoding, tmux naming, commit rules
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../SETUP.md](../SETUP.md) — recording pipeline

## Goal

Record yourself autonomously exploring AI/open-source topics for 30 seconds. Produce a vertical (608×1080) video with GPU-accelerated encoding and zero disk I/O (tmpfs). Narrate your actions and decisions in real-time using edge-tts.

You are an autonomous content creator. Decide what to do, do it, narrate it, record it. Be creative and exploratory.

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
2. Open Chrome/Epiphany in your display
3. Start edge-tts narration in background
4. Begin ffmpeg recording (x11grab + VAAPI)
5. Do your work: browse, read, explore, write code
6. After 30s, stop recording
7. Verify the video
8. Commit your work
```

## Tools available

- **Browser**: `google-chrome --no-sandbox --window-size=608,1080 --new-window "URL"` or `epiphany`
- **Recording**: `ffmpeg -vaapi_device /dev/dri/renderD128 -f x11grab -video_size 608x1080 -i :99.0 -t 30 -vf "format=nv12,hwupload" -c:v h264_vaapi -b:v 4M capture.mp4`
- **Narration**: `edge-tts --voice es-CO-GonzaloNeural --text "..." --write-media narration.mp3` (run in background)
- **Text-to-speech**: Use `edge-tts` with Colombian voice. Never use espeak.
- **Python http server**: `python3 -m http.server PORT` for serving local files
- **AI topics to explore**: trending repos on github.com, huggingface spaces, new models, AI frameworks, memory systems, orchestration, agents, etc.
- **Write findings**: save notes, code snippets, or discoveries to files in your directory

## Files

- `capture.mp4` — your recorded video
- `narration.log` — what you narrated (optional)
- Any other files you create during exploration

## Recording specifics

```bash
export DISPLAY=:99
export LIBVA_DRIVER_NAME=radeonsi

# Start recording
ffmpeg -vaapi_device /dev/dri/renderD128 \
  -f x11grab -video_size 608x1080 -i :99.0 \
  -t 30 \
  -vf "format=nv12,hwupload" \
  -c:v h264_vaapi -b:v 4M \
  -y capture.mp4 &
REC_PID=$!
```

## Verification

After recording, check:
- File exists: `stat capture.mp4`
- File size > 1 MB
- Resolution correct: `ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 capture.mp4`
- Not corrupt: `ffprobe -v error capture.mp4`

## Cleanup

```bash
kill $REC_PID $BROWSER_PID 2>/dev/null
```

## Self-command

All commands in background. Self-wake after each step.

```bash
(sleep <N>; tmux send-keys -t 5-3 "Self-wake: <context>" Enter) &
```
