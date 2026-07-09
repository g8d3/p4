# ag-03 — Generate Audio

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, TTS tools
- [../AGENTS.md](../AGENTS.md) — pipeline flow, models, TTS

## Model
`opencode-go/deepseek-v4-flash` (fast for orchestration)

## Goal

Read `../ag-02/output/scripts-manifest.csv` and generate audio for each script using multiple TTS engines.

## Input

`../ag-02/output/scripts-manifest.csv` — scripts to convert to audio.
`../ag-02/output/script-NNN.md` — script content.

## Output

- `output/script-001/edge-jenny.mp3` — edge-tts with Jenny voice
- `output/script-001/edge-guy.mp3` — edge-tts with Guy voice
- `output/script-001/mimo-mia.mp3` — Xiaomi TTS with Mia voice
- `output/script-001/metadata.json` — TTS configuration used
- `output/audio-manifest.csv` — index of all audio files

### Audio manifest (audio-manifest.csv)
```csv
audio_id,script_id,tts_engine,voice,file_path,duration_sec
001-001,001,edge-tts,en-US-JennyNeural,script-001/edge-jenny.mp3,120
001-002,001,edge-tts,en-US-GuyNeural,script-001/edge-guy.mp3,120
001-003,001,mimo-tts,Mia,script-001/mimo-mia.mp3,120
```

## Process

1. Read `../ag-02/output/scripts-manifest.csv`
2. For each script, extract text content
3. Generate audio with each TTS engine:
   - edge-tts (Jenny + Guy)
   - Xiaomi mimo-v2.5-tts (Mia)
4. Save audio files to `output/script-NNN/`
5. Write manifest to `output/audio-manifest.csv`

## TTS Commands

### edge-tts
```bash
edge-tts --text "Script text here" --voice en-US-JennyNeural --write-media output.mp3
edge-tts --text "Script text here" --voice en-US-GuyNeural --write-media output.mp3
```

### Xiaomi mimo-v2.5-tts
```bash
source ~/.zshrc
curl -s -k "$XIAOMI_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $XIAOMI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mimo-v2.5-tts",
    "messages": [
      {"role": "user", "content": "Di esto: SCRIPT_TEXT"},
      {"role": "assistant", "content": "SCRIPT_TEXT"}
    ],
    "modalities": ["audio"],
    "audio": {"voice": "Mia", "format": "mp3"}
  }' | python3 -c "import sys,json,base64; open('output.mp3','wb').write(base64.b64decode(json.load(sys.stdin)['choices'][0]['message']['audio']['data']))"
```

## Self-command

```bash
tmux send-keys -t 15-3 "echo running ag-03" Enter
```

## Verification

1. All audio files exist and are non-empty
2. Audio files are playable (`ffprobe output.mp3`)
3. Manifest CSV is valid
4. Duration matches script length estimate
