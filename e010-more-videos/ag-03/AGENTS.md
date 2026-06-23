# ag-03 — TTS/ASR with Xiaomi MIMO + video narration

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, security
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Model
`zai-coding-plan/glm-4.7` (lighter on credits than glm-5.x — use higher tier only for final polish)

## Goal
Screen-record a demonstration of Xiaomi MIMO's TTS and ASR APIs. Show the terminal commands, play the TTS output, transcribe audio back. Must be an actual Wayland screen recording.

## Critical: You are a human teacher, not a script runner

You MUST interact with the system in real-time:
- Think as you go, explain your reasoning as you type each command
- Read the output, react to it, explain what it means
- Do NOT pre-write a script, execute it, and narrate over the recording
- Pace yourself for human consumption

## What to do

1. Read existing Xiaomi API scripts in `~/code/p4/e009-xiaomi-display/ag-01/` (reference only)
2. Set up a virtual display with Sway (Wayland) — 608x1080 vertical
3. Record the screen with `wf-recorder` while you work
4. Demonstrate live:
   - TTS: "Let me try converting this text to speech..." type command, play result, react
   - ASR: "Now let me transcribe that audio back..." type command, show result
5. Think out loud: explain what each API does, why you'd use it, what the output means
6. LEAVE SILENCE when TTS plays — do NOT talk over the demo audio
7. Structure: intro (TTS/ASR?) → body (live demo of both) → conclusion (quality, latency, use cases)
8. Add subtitles (TikTok-style)
9. Output to `./output/`
10. Self-review: check video shows real terminal interaction, audio is clean

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
- **CRITICAL: Fill ALL gaps** — every second of video must have either narration or TTS audio. No silent gaps (except intentional TTS playback silence). Check with `ffmpeg -filter:a volumedetect` at 2s intervals.

## Pipeline (v2+)

The pipeline is split into stages so each can be debugged independently:

```
record.sh          → Sway headless + wf-recorder + foot terminal demo
  output: recording_raw.mp4 (video only), timing.events, record_timing.json
mix_audio.py       → edge-tts narration + TTS audio mix (reads timing.events)
  output: audio_final.wav, subtitle_timing.json
gen_subtitles.py   → TikTok-style SRT
  output: subtitles.srt
finalize.sh        → trim + burn subtitles + mux audio → final demo.mp4
  output: demo.mp4, metadata.json
```

### Stage timing (v1 measurements)
- Sway headless startup: ~3s
- wf-recorder + foot demo: ~60s (real time)
- Audio mix (8 sources): ~3s
- Finalize (subtitles + mux): ~5s
- **Total: ~75s per iteration**

## Pitfalls learned (read before each iteration)

### foot terminal
- `--no-config` does NOT exist. Use `-c /dev/null` or just omit.
- `-e` is IGNORED (compat only). Pass command as positional args: `foot -f "mono:size=14" bash demo.sh`
- `-F` = fullscreen, `-w WxH` = window size in pixels, `-W WxH` = in chars.

### Sway headless
- Set `WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1`.
- Sway may NOT honor `WAYLAND_DISPLAY` — it creates its own socket name. Always detect dynamically:
  ```bash
  WL=$(ls -t "$XDG_RUNTIME_DIR"/wayland-* 2>/dev/null | head -1)
  ```
- IPC socket: `SWAYSOCK=$(ls "$XDG_RUNTIME_DIR"/sway-ipc.* | sort -t. -k4 -n | tail -1)`
- Output config: `output HEADLESS-1 resolution 608x1080` in sway config.

### wf-recorder
- `-D` (no-damage) is REQUIRED — without it, static screens don't produce frames.
- `-r 15` for constant 15fps.
- Does NOT support `--codec` or `--no-audio` flags. Use `-c h264_vaapi -d /dev/dri/renderD128`.
- Video-only recording is fine — mix audio in post for precise timing.

### ffmpeg audio mixing
- **ADTS (.aac) container does NOT store duration correctly** — ffprobe reports wrong duration. Use `.wav` or `.m4a` for intermediate files. Never `.aac`.
- `amix=duration=longest` stops when the longest INPUT ends, NOT when silence ends. To ensure full duration, add `anullsrc` (infinite silence) as an extra input.
- `adelay=Ms|Ms` delays audio by Ms milliseconds. Works correctly even for large values (50s+).

### ffmpeg subtitles (subtitles filter)
- **MarginV is in ASS script pixels, not video pixels.** Default PlayResY=288.
  - `MarginV=80` → text at ~70% screen height (mid-screen!). WRONG.
  - `MarginV=10` → text at ~96% screen height (bottom). CORRECT for TikTok.
- force_style with PrimaryColour/OutlineColour parameters can silently break rendering. Test each param individually.
- Working TikTok style: `force_style='Bold=1,FontSize=26,Outline=3,Shadow=1,Alignment=2,MarginV=10'`
- The `subtitles` filter burns text into video pixels (hardsubs). Softsubs need different approach.

### Audio gap detection
- After mixing, ALWAYS run `volumedetect` at 2s intervals to find silent gaps.
- Any gap below -40 dB lasting >2s is a bug — add narration to fill it.
- v1 had a 4.7s silence gap during ASR API call (43-48s). Fix: add a narration segment for the ASR processing phase.

### Subtitle coverage
- Subtitles must cover the ENTIRE video. No gaps >3s without subtitles.
- During TTS playback, show "[AI Voice]" or "▶ Playing TTS Audio" subtitle (the section is intentionally silent for narration, but subtitles should continue).

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
- Subtitles present (covering entire video, no gaps >3s)
- No audio gaps >2s below -40 dB (except intentional TTS silence)
- metadata.json present
- No API keys or secrets in any file

## Iteration history

### v1 (demo.mp4) — 2026-06-23
- Duration: 57s, 608x1080, real wf-recorder screen capture.
- Issues found:
  1. 4.7s silence gap during ASR API call (43-48s)
  2. No subtitles during TTS playback (23.5-37s)
  3. Subtitle gap during ASR processing (45.5-48.5s)
  4. No VAAPI encoding in wf-recorder (software h264)
- Process failures: foot `--no-config`, AAC duration bug, MarginV=80 placement, Sway socket detection.

### v2 (demo.mp4) — 2026-06-23
- Duration: 53s, 608x1080, wf-recorder with VAAPI encoding.
- Fixes from v1:
  1. Added `06_asr_process` narration segment — fills the 4.7s gap during ASR API call
  2. Subtitles now cover TTS playback ("▶ Playing TTS Audio" / "[AI Voice]")
  3. Dynamic subtitle timing from `timing.events` — no hardcoded gaps
  4. VAAPI encoding in wf-recorder (`-c h264_vaapi -d /dev/dri/renderD128`)
- Verification: 0 silence gaps, 15/15 subtitle checkpoints pass.
- Remaining issues for v3:
  1. t=38s audio at -35.5 dB (transition between segments — borderline)
  2. Unicode glyph ▶ not found in Arimo-Bold font (falls back, but ugly)
  3. Video bitrate low (214 kbps) — terminal content compresses too well
  4. No visual interest during API calls (just "Calling API..." text)

### v3 (demo.mp4) — 2026-06-23
- Duration: 50.7s, 608x1080, shared `../bin/record.sh` + VAAPI re-encode.
- Fixes from v2:
  1. Spinner animation during API calls (rotating `-\|/` character)
  2. Progress bar during TTS playback (visual `###` fill)
  3. Input text displayed before TTS command
  4. Used shared `../bin/record.sh` instead of custom recording pipeline
  5. All audio levels above -28.5 dB (was -35.5 dB at transitions in v2)
  6. Bitrate improved: ~878 kbps raw (was 214 kbps in v2)
- Process learnings:
  - Must `rm -f` stale output files before recording — wf-recorder prompts for overwrite
  - VAAPI re-encode from yuv444p source works if raw file is fresh
  - Shared script hardcodes `wayland-1` — works reliably
  - To launch demo: background record.sh, wait 4s, use `swaymsg -t command 'exec foot --maximized bash demo.sh'`
- Verification: 0 silence gaps (all > -28.5 dB), subtitles cover 0.5-51.7s continuously.
- Remaining issues for v4:
  1. Unicode glyph ▶ still in subtitles (need to replace with ASCII)
  2. ASR result has mixed Chinese/Spanish characters (interesting but messy)
  3. No color visual interest — mostly green/white text on dark background
  4. Could add comparison table or quality metrics on screen
