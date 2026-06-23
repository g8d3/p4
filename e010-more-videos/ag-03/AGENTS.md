# ag-03 — TTS/ASR with Xiaomi MIMO + video narration

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Model
`opencode-go/mimo-v2.5` (has vision for self-review)

## Goal
Use Xiaomi MIMO's free TTS and ASR models to generate narration for videos. Record a screencast demonstrating the TTS/ASR pipeline.

## What to do

1. Read the existing Xiaomi API scripts in `~/code/p4/e009-xiaomi-display/ag-01/`
2. Set up a virtual display (608x1080)
3. Demonstrate:
   - TTS: Convert text to speech using Xiaomi's voice models
   - ASR: Transcribe an audio file using Xiaomi's ASR
4. Create a narrated video showing the API in action
5. Self-review the video quality

## Xiaomi API

```bash
XIAOMI_API_KEY=REVOKED
XIAOMI_BASE_URL=https://token-plan-sgp.xiaomimimo.com/v1
```

Available voice: `es-CO-SalomeNeural` (Colombian Spanish, matches our TTS convention).

## Success criteria
- TTS produces audible speech from text
- ASR transcribes audio to text
- Video demonstrates both features
- Video is 608x1080 vertical format
- Narration is in Colombian Spanish voice
