# ag-01 — Virtual display + recording pipeline

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Model
`opencode-go/mimo-v2.5` (has vision for self-review)

## Goal
Record a screencast of a terminal doing something interesting (typing commands, editing code, browsing files). Must be an actual screen recording via Wayland, not a composited video. Include audio narration and subtitles.

## Critical: You are a human teacher, not a script runner

You MUST interact with the system in real-time:
- Think as you go, explain your reasoning as you type each command
- Read the output, react to it, explain what it means
- Do NOT pre-write a script, execute it, and narrate over the recording
- Do NOT type faster than a human can follow — pause, explain, show

## What to do

1. Set up a virtual display with Sway (Wayland) — 608x1080 vertical
2. Open a terminal window (foot) in the virtual display
3. Record the screen with `wf-recorder` while you work
4. Think out loud: "First let me check what's in this directory... I see a config file, let me open it... interesting, the timeout is set to 30s, let me increase it..."
5. Let the system respond, then react to its output
6. Structure your video: intro (what you'll do and why) → body (live work with live thinking) → conclusion (findings + call to action / cliffhanger)
7. Add subtitles via ffmpeg drawtext (TikTok-style)
8. Add narration via edge-tts if needed, or narrate live
9. Output final video to `./output/`
10. Self-review: check resolution, content, sync, pacing

## Recording — use shared tool

```bash
../ag-00/bin/record.sh my_demo 60
```

That's it. Starts Sway, opens terminal, records for 60 seconds, saves to `./output/my_demo.mp4`. Do NOT write custom recording scripts. Do NOT configure sway manually. Do NOT use ffmpeg encoding pipelines. The shared script handles everything.

If you need a longer demo, record in segments:
```bash
../ag-00/bin/record.sh part1_intro 30
../ag-00/bin/record.sh part2_body 60
```

## Critical pipeline notes (learned from video 1 failures)

1. **`--no-dmabuf` is MANDATORY** for wf-recorder with Sway headless. Without it, all frames are black (0 bytes). The DMA-BUF capture path doesn't work with headless Vulkan renderer.
2. **`--no-damage` is MANDATORY** for headless. The headless backend doesn't emit damage events, so wf-recorder never captures frames without this flag.
3. **Use `-c libx264` for capture**, not `h264_vaapi`. The VAAPI encoder in wf-recorder produces tiny corrupt files from headless. Re-encode with VAAPI afterward via ffmpeg.
4. **Demo script must run INSIDE foot terminal**: `foot --maximized bash demo_script.sh` — NOT `bash demo_script.sh &` (that runs in background, output doesn't go to Wayland display).
5. **Narration must match video duration**. Generate narration first, check its duration with ffprobe, then pace the demo to match. A 37s narration on a 19s video gets cut off.
6. **Subtitles must be actual narration text**, not labels. Use the same text as the TTS script.
7. **Subtitle font size ≤ 10** for 608x1080. Larger fonts overlap terminal content.
8. **Sway config**: `xwayland disable` to avoid X0 socket conflicts with existing Xorg.

## Self-review checklist (after each video)

Use your vision capability to examine 4+ frames (beginning, 25%, 50%, 75%):
- [ ] Content visible and readable? (not black/blank)
- [ ] Resolution 608x1080 vertical?
- [ ] Terminal text not cut off at edges?
- [ ] Subtitles present, readable, NOT overlapping content?
- [ ] Subtitles match narration audio?
- [ ] Audio present and synced?
- [ ] Video duration ≈ narration duration?
- [ ] Intro visible? Conclusion visible?
- [ ] > 5 MB file size?

## Video metadata
Each video must include a `metadata.json` in `./output/` with:

```json
{
  "duration_sec": 120,
  "resolution": "608x1080",
  "display": "wayland-sway-headless",
  "capture_method": "wf-recorder",
  "encoding": "h264_vaapi",
  "audio": true,
  "subtitles": true,
  "cpu_usage_avg": 45.2,
  "ram_mb": 512,
  "gpu_usage_avg": 12.5,
  "narration": "es-CO-SalomeNeural",
  "narration_method": "edge-tts",
  "recording_start": "2026-06-23T10:00:00",
  "recording_end": "2026-06-23T10:02:00"
}
```

## Success criteria
- Video file exists and is > 5 MB
- Resolution is 608x1080 vertical
- Content is visible and readable
- Audio is present (narration + demo sounds)
- Subtitles are present and match narration
- No black/blank frames
- metadata.json is present
- Video duration matches narration duration (±2s)

## Iteration log

### Video 1 (2026-06-23)
- **Duration**: 19.3s (narration 37.4s — cut off)
- **Size**: 4.6MB (slightly under 5MB target)
- **What worked**: Wayland headless capture with `--no-dmabuf --no-damage`, VAAPI encoding, edge-tts
- **What failed**: 
  - DMA-BUF capture → black frames (fixed with `--no-dmabuf`)
  - `--no-damage` required for headless (wf-recorder never captures without it)
  - Demo script ran in background instead of inside foot terminal (first attempt)
  - VAAPI encoder in wf-recorder produced corrupt files (use libx264 then re-encode)
  - Narration 2x longer than video — second half cut off
  - Subtitles too large (FontSize=20 → 11), still overlap content
  - Subtitles were labels, not narration text
  - No intro/conclusion structure
  - No interactivity — just ran a pre-written script

### Video 2 (2026-06-23)
- **Duration**: 16.9s (matches narration 16.9s)
- **Size**: 3.7MB (under 5MB target)
- **Improvements**: 
  - Generated narration FIRST, paced demo to match
  - Subtitles = actual narration text (not labels)
  - FontSize=10, no content overlap
  - Intro banner + conclusion banner
- **Remaining issues**:
  - Terminal text wraps at 608px (need larger display or smaller font)
  - Still scripted, not live interactive
  - File size under 5MB — need longer video or higher bitrate
  - Subtitles could use background box for better readability

### Video 3 (2026-06-23) — using shared record.sh
- **Duration**: 21s (narration)
- **Size**: 423KB (under 5MB)
- **What worked**: Used `../ag-00/bin/record.sh demo 60` — one command, no custom scripts
- **What failed**: record.sh opens empty terminal (`foot --maximized &`), no demo content appears. Terminal shows only zsh prompt with git branch.
- **Root cause**: Without keyboard simulation (ydotool/wtype), cannot type into Wayland terminal. record.sh is a recording tool, not a content tool.
- **Fix needed**: record.sh should accept optional script parameter: `record.sh demo 60 my_script.sh` — runs script inside foot instead of empty shell.
