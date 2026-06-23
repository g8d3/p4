# ag-02 — Resource monitoring comparison screencast

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Model
`xiaomi/mimo-v2.5` (has vision for self-review)

## Goal
Record a SCREENCAST (not text analysis) comparing resource usage between two providers. Show real-time monitoring tools on screen. Must be an actual Wayland screen recording.

## What to do

1. Set up a virtual display with Sway (Wayland) — 608x1080 vertical
2. Open multiple terminals showing:
   - `htop` or `btm` for CPU/RAM
   - `nvidia-smi` or `radeontop` for GPU
   - A script running inference on two providers sequentially
3. Record the screen with `wf-recorder`
4. Show the comparison visually: run the same prompt on both providers
5. Add subtitles (TikTok-style)
6. Add narration via edge-tts (es-CO-SalomeNeural)
7. Output to `./output/`
8. Self-review: verify video shows real monitoring tools, not just text

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
