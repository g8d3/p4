# ag-02 — Full Video Pipeline

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, TTS tools, GPU encoding
- [../AGENTS.md](../AGENTS.md) — pipeline architecture

## Model
`opencode-go/deepseek-v4-flash`

## Goal

Take 1 topic and produce 1 complete video: script → voice → transcription → video → merge.

## Input

- `../ag-01-research/output/topics.csv` — topics to process
- Your assigned topic number (given by orchestrator)

## Output

Work in your assigned subdirectory: `agent-NNN/`

```
agent-001/
├── script.md          # Written script
├── audio.mp3          # Voice over (edge-tts)
├── subtitles.srt      # Transcription with timestamps
├── video.mp4          # Rendered video (no audio)
└── FINAL.mp4          # Merged audio + video
```

## Process

### Step 1: Write Script
Read your topic from topics.csv. Write a script with:
- Intro (10-15 sec)
- Body (60-90 sec, 2-3 key points)
- Conclusion (10-15 sec)

Save as `script.md`

### Step 2: Generate Voice Over
Extract spoken text from script (no markdown headers). Generate audio:
```bash
edge-tts --text "SCRIPT_TEXT" --voice en-US-JennyNeural --write-media audio.mp3
```

### Step 3: Transcribe
Use Xiaomi ASR to get subtitles with timestamps:
```bash
source ~/.secrets/.env
base64_audio=$(base64 -w0 audio.mp3)
curl -s -k "$XIAOMI_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $XIAOMI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mimo-v2.5-asr",
    "messages": [{"role": "user", "content": [
      {"type": "input_audio", "input_audio": {"data": "data:audio/mp3;base64:'"$base64_audio"'", "format": "mp3"}}
    ]}]
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

Convert transcription to SRT format with timestamps.

### Step 4: Render Video
Create video with burned-in subtitles:
```bash
ffmpeg -f lavfi -i color=c=black:s=608x1080:d=DURATION \
  -vf "subtitles=subtitles.srt:force_style='FontSize=24,PrimaryColour=&Hffffff'" \
  -c:v h264_vaapi -vaapi_device /dev/dri/renderD128 \
  -vf "format=nv12,hwupload" \
  video.mp4
```

### Step 5: Merge Audio + Video
```bash
ffmpeg -i video.mp4 -i audio.mp3 \
  -c:v copy -c:a aac -b:a 192k \
  FINAL.mp4
```

## Self-command

```bash
tmux send-keys -t 15-2-N "echo running ag-02 topic N" Enter
```

## Verification

1. All files exist in your agent-NNN/ directory
2. audio.mp3 is playable
3. subtitles.srt is valid SRT format
4. FINAL.mp4 has both video and audio streams
5. Video duration matches audio duration
