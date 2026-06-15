# ag-05 — Kokoro TTS explorer

## Model
`opencode-go/mimo-v2.5`

## Goal

Figure out how to use Kokoro TTS through the Chutes API (`$CHUTES_API_KEY`), and document the usage in fundamentals.

## Context

- Chutes API key exists as `CHUTES_API_KEY` env var
- Standard OpenAI TTS endpoint (`/v1/audio/speech`) returns 404
- `/v1/models` also returns 404
- The API base is `https://api.chutes.ai`
- The model might be accessed differently (maybe via `/v1/chat/completions` or a custom endpoint)
- Kokoro TTS supports many voices (af_heart, af_bella, am_adam, etc.)
- Output must be MP3 or Opus, NOT WAV

## Task

### 1. Discover the API
Try different endpoints and model names. The Chutes API might use:
- `/v1/completions` with specific format
- A custom endpoint pattern like `/v1/run/{model_name}`
- Check if `kokoro` is the right model name or something else
- Check the Chutes docs/status page

Try variations:
```bash
curl -s "https://api.chutes.ai/v1/chat/completions" -H "Authorization: Bearer $CHUTES_API_KEY" ...
curl -s "https://api.chutes.ai/kokoro" -H "Authorization: Bearer $CHUTES_API_KEY" ...
```

### 2. Once working, test voices
List available Kokoro voices and test a few:
- af_heart, af_bella, af_nicole, af_sarah (female)
- am_adam, am_michael, am_liam (male)

### 3. Generate a test file
Produce a short TTS test with Kokoro → MP3.

### 4. Document in fundamentals
Add to `e000-fundamentals/AGENTS.md`:
```
## TTS

### Kokoro (via Chutes API)
```bash
curl -s -X POST "https://api.chutes.ai/..." \
  -H "Authorization: Bearer $CHUTES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"kokoro","input":"Text here","voice":"af_heart","response_format":"mp3"}' \
  -o output.mp3
```
```

### 5. Update ag-01's AGENTS.md
Replace edge-tts in Step 5 with the Kokoro TTS command.

## Self-command
ALL commands: `>/dev/null 2>&1 &`. Self-wake. Never synchronous.
