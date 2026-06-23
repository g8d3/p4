# ag-02 — Resource monitoring comparison screencast

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Model
`xiaomi/mimo-v2.5` (has vision for self-review)

## Goal
Record a SCREENCAST (not text analysis) comparing resource usage between two providers. Show real-time monitoring tools on screen. Must be an actual Wayland screen recording.

## Critical: You are a human teacher, not a script runner

You MUST interact with the system in real-time:
- Think as you go, explain your reasoning as you type each command
- Read the output, react to it, explain what it means
- Do NOT pre-write a script, execute it, and narrate over the recording
- Pace yourself for human consumption — let the viewer read, process, follow

## What to do

1. Set up a virtual display with Sway (Wayland) — 608x1080 vertical
2. Open multiple terminals showing live tools
3. Record the screen with `wf-recorder` while you work
4. Think out loud: explain each tool, what you're looking for, what the numbers mean
5. Run the same prompt on both providers — react to the results live
6. Structure: intro (why compare?) → body (live demo) → conclusion (which is faster/cheaper?)
7. Add subtitles (TikTok-style)
8. Add narration via edge-tts if needed
9. Output to `./output/`
10. Self-review: verify video shows real interaction, not static text

## Audio guidelines
- Narrate over the demo, but LEAVE SILENCE when playing TTS samples or demo audio
- Do NOT talk over demo audio — let it play

## Video metadata
Include `./output/metadata.json`:

```json
{
  "duration_sec": 180,
  "resolution": "608x1080",
  "display": "wayland-sway-headless",
  "capture_method": "wf-recorder",
  "encoding": "h264_vaapi",
  "audio": true,
  "subtitles": true,
  "cpu_usage_avg": 35.0,
  "ram_mb": 768,
  "gpu_usage_avg": 8.0,
  "providers_compared": ["opencode-go/deepseek-v4-flash", "xiaomi/mimo-v2.5"],
  "narration": "es-CO-SalomeNeural",
  "recording_start": "",
  "recording_end": ""
}
```

## Success criteria
- Video shows live monitoring tools on screen (not static text)
- Both providers are demonstrated
- Audio narration present
- Subtitles present
- 608x1080 vertical
- metadata.json present
