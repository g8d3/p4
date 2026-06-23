# ag-03 — TTS/ASR with Xiaomi MIMO + video narration

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, security
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Model
`zai-coding-plan/glm-5v-turbo` (has vision for self-review)

## Goal
Screen-record a demonstration of Xiaomi MIMO's TTS and ASR APIs. Show the terminal commands, play the TTS output, transcribe audio back. Must be an actual Wayland screen recording.

## What to do

1. Read existing Xiaomi API scripts in `~/code/p4/e009-xiaomi-display/ag-01/` (reference only)
2. Set up a virtual display with Sway (Wayland) — 608x1080 vertical
3. Record the screen with `wf-recorder`
4. Demonstrate:
   - TTS: Convert text to speech using Xiaomi's voice models
   - ASR: Transcribe an audio file using Xiaomi's ASR
5. Narrate the demo, but LEAVE SILENCE when TTS is playing — do NOT talk over the TTS audio
6. Add subtitles (TikTok-style, bottom position)
7. Output to `./output/`
8. Self-review: check video shows real terminal interaction, audio is clean

## Xiaomi API

Use environment variables (NEVER hardcode keys in files):

```bash
export XIAOMI_API_KEY=tp-xxx
export XIAOMI_BASE_URL=https://token-plan-sgp.xiaomimimo.com/v1
```

Available voice: `es-CO-SalomeNeural` (Colombian Spanish).

## Audio guidelines
- Narrate your actions and explain what you're doing
- When TTS plays, STOP talking — let the TTS audio be heard clearly
- Resume narration after TTS finishes

## Video metadata
Include `./output/metadata.json`:

```json
{
  "duration_sec": 150,
  "resolution": "608x1080",
  "display": "wayland-sway-headless",
  "capture_method": "wf-recorder",
  "encoding": "h264_vaapi",
  "audio": true,
  "subtitles": true,
  "apis_demoed": ["xiaomi-tts", "xiaomi-asr"],
  "tts_voice": "es-CO-SalomeNeural",
  "narration": "es-CO-SalomeNeural",
  "narration_method": "edge-tts",
  "recording_start": "",
  "recording_end": ""
}
```

## Success criteria
- TTS produces audible speech (not talked over by narration)
- ASR transcribes audio to text correctly
- Video shows real terminal commands (not a composited animation)
- 608x1080 vertical
- Subtitles present
- metadata.json present
- No API keys or secrets in any file
