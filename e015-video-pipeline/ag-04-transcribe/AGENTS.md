# ag-04 — Transcribe Audio

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles
- [../AGENTS.md](../AGENTS.md) — pipeline flow, models

## Model
`opencode-go/deepseek-v4-flash` (fast for orchestration)

## Goal

Read `../ag-03/output/audio-manifest.csv` and transcribe each audio file to text with timestamps.

## Input

`../ag-03/output/audio-manifest.csv` — audio files to transcribe.
`../ag-03/output/script-NNN/*.mp3` — audio files.

## Output

- `output/script-001/edge-jenny.srt` — SRT subtitles
- `output/script-001/edge-jenny.txt` — plain text
- `output/script-001/edge-jenny-timestamps.json` — word-level timestamps
- `output/transcribe-manifest.csv` — index of all transcriptions

### Transcription manifest (transcribe-manifest.csv)
```csv
transcription_id,audio_id,format,word_count,duration_sec,srt_file
001-001,001-001,srt,180,120,script-001/edge-jenny.srt
```

## Process

1. Read `../ag-03/output/audio-manifest.csv`
2. For each audio file, transcribe using:
   - whisper.cpp (local, fast) OR
   - Xiaomi mimo-v2.5-asr (cloud, accurate)
3. Generate SRT subtitles with timestamps
4. Save to `output/script-NNN/`
5. Write manifest to `output/transcribe-manifest.csv`

## Transcription Commands

### whisper.cpp (local)
```bash
./main -m models/ggml-base.en.bin -f input.wav -oxt srt -of output
```

### Xiaomi mimo-v2.5-asr
```bash
source ~/.zshrc
base64_audio=$(base64 -w0 input.mp3)
curl -s -k "$XIAOMI_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $XIAOMI_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"mimo-v2.5-asr\",
    \"messages\": [
      {\"role\": \"user\", \"content\": [
        {\"type\": \"input_audio\", \"input_audio\": {\"data\": \"data:audio/mp3;base64,$base64_audio\", \"format\": \"mp3\"}}
      ]}
    ]
  }" | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

## Self-command

```bash
tmux send-keys -t 15-4 "echo running ag-04" Enter
```

## Verification

1. SRT files exist and are valid format
2. Text files exist and are non-empty
3. Timestamps align with audio duration
4. Manifest CSV is valid
