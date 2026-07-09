# ag-02 — Xiaomi TTS/ASR Tested Scripts

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — TTS tools
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Model
`opencode-go/deepseek-v4-flash`

## Goal

Save tested Xiaomi TTS and ASR scripts from session 2026-07-09.

## Output

`output/xiaomi-api-tested.sh` — tested script for TTS and ASR.

## Tested Commands

### TTS (Text-to-Speech)
```bash
source ~/.secrets/.env
curl -s -k "$XIAOMI_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $XIAOMI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mimo-v2.5-tts",
    "messages": [
      {"role": "user", "content": "Di esto: TEXT_HERE"},
      {"role": "assistant", "content": "TEXT_HERE"}
    ],
    "modalities": ["audio"],
    "audio": {"voice": "Mia", "format": "wav"}
  }' | python3 -c "import sys,json,base64; open('output.wav','wb').write(base64.b64decode(json.load(sys.stdin)['choices'][0]['message']['audio']['data']))"
```

### ASR (Speech-to-Text)
```bash
source ~/.secrets/.env
base64_audio=$(base64 -w0 audio.wav)
curl -s -k "$XIAOMI_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $XIAOMI_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"mimo-v2.5-asr\",
    \"messages\": [
      {\"role\": \"user\", \"content\": [
        {\"type\": \"input_audio\", \"input_audio\": {\"data\": \"data:audio/wav;base64,$base64_audio\", \"format\": \"wav\"}}
      ]}
    ]
  }" | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

### Available Voices
Mia, Chloe, Milo, Dean, 冰糖, 茉莉, 苏打, 白桃, mimo_default

### Available Models
- mimo-v2.5
- mimo-v2.5-asr
- mimo-v2.5-pro
- mimo-v2.5-tts
- mimo-v2.5-tts-voiceclone
- mimo-v2.5-tts-voicedesign
