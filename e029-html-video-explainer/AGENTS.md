# e029 — HTML Video Explainer

Experiment goal: render a **video from HTML** using HyperFrames — an explainer for a
non-technical Spanish-speaking audience that teaches how a cheap toolkit (Android phone +
Termux + SSH + computer + OpenCode Go + DeepSeek Flash) gives you an AI developer/designer
working for you. The video is also a self-explanation: it shows how it was made (web
templates + HTML, no heavy programs like Open Design).

## Deliverable

`videos/phone-ai-developer/renders/video.mp4` — 58.3s, 1920×1080, h264, Spanish narration
(Deepgram Aura-2 `aura-2-celeste-es`) with **karaoke captions** (Deepgram Nova-3
transcription, 66 caption groups).

## TTS research

See [`TTS-RESEARCH.md`](TTS-RESEARCH.md): leaderboard leaders, emotion-capable providers
(Fish Audio S2.1 Pro `[tag]` control, Deepgram Flux, Hume Octave 2, ElevenLabs, Cartesia,
MiniMax), and p4's ready-to-use keys (Deepgram, KIE Gemini). Reusable wrappers:
[`bin/dg-tts.sh`](bin/dg-tts.sh) (TTS) and [`bin/dg-transcribe.sh`](bin/dg-transcribe.sh)
(STT → word timestamps → captions).

## Project layout

```
e029-html-video-explainer/
└── videos/phone-ai-developer/     ← HyperFrames project
    ├── BRIEF.md                    ← confirmed intent
    ├── STORYBOARD.md               ← 9 frames, video direction, shot sequences
    ├── SCRIPT.md                   ← Spanish narration
    ├── frame.md                    ← Capsule design preset (adopted)
    ├── capture/extracted/          ← synthetic source package (no web capture)
    ├── compositions/frames/        ← 9 sub-compositions (one per frame)
    ├── assets/voice + assets/sfx/  ← Kokoro TTS + SFX
    ├── assets/fonts/               ← Bodoni Moda + Space Grotesk (woff2 local)
    ├── snapshots/                  ← contact sheets + Gemini analysis
    └── renders/video.mp4           ← final render
```

## How to run

```bash
cd videos/phone-ai-developer
npm run dev          # preview at http://localhost:3002
npm run check        # lint + runtime + layout + motion + contrast
npm run render       # render to renders/video.mp4
```

## Pipeline notes (what worked)

- **Routing**: `/hyperframes` → faceless-explainer (no website, no capture — invented visuals).
- **Design preset**: Capsule (playful editorial: cream, ink pills, Bodoni Moda + Space Grotesk,
  candy pastels, grain + radial glows). Chosen for a warm, friendly, non-technical feel.
- **Narration**: **Deepgram Aura-2 `aura-2-celeste-es`** (es-co Colombian, energetic/friendly)
  via `../bin/dg-tts.sh` (REST `/v1/speak`, MP3 default — p4 convention, no WAV).
  The HyperFrames `audio.mjs` default falls back to local **Kokoro** (`ef_dora`) when no
  HeyGen credential exists — first pass used that; re-voiced with Deepgram for a more
  natural Spanish voice.
- **Transcription is MANDATORY before anything downstream**: generated audio must be
  transcribed to word timestamps before captions can be built (captions.mjs reads
  `audio_meta.json -> voices[].words`). Use **Deepgram Nova-3** via `../bin/dg-transcribe.sh`
  (`/v1/listen?model=nova-3&language=es&smart_format=true`) — returns `words[]` with
  `{word, start, end}`. Write them into `audio_meta.json` as `{id, text, start, end}`,
  then run `captions.mjs build`. First pass skipped this (captions were dropped); it is
  now part of the pipeline.
- **BGM**: needs a HeyGen credential (retrieve-only, no offline fallback) → video is
  narration + SFX only. SFX are a bundled local library (chime, pop, whoosh, typing, ...).
- **captions.mjs symlink gotcha**: running it via the `~/.config/opencode/skills/...`
  path (a symlink) makes the CLI guard silently no-op (exit 0, no output) because
  `process.argv[1]` ≠ `import.meta.url`. Run it via the realpath
  `~/.claude/skills/faceless-explainer/scripts/captions.mjs`.
- **Fonts**: `@font-face` must reference local `.woff2` (no CDN in sub-compositions).
  Bodoni Moda and Space Grotesk are variable fonts; one latin woff2 each covers all weights.
  Downloaded from Google Fonts CSS API with a modern UA to get woff2 URLs.
- **Subagents**: this environment has only `build` (primary) and no general subagent, so the
  9 frame workers were executed **inline serially** instead of dispatched (contract fallback).
- **Frame 03 fix**: `document.getElementById("#id")` with a `#` prefix returns null —
  `getTotalLength()` crashed. Use plain ids in `getElementById`.
- **Frame 09 fix**: verbs lingering at 55% opacity under the closing pill triggered
  `content_overlap`; the closing beat must fully retire the verbs.
- **Clip lanes**: the full-bleed background AND the grain layer are both timed clips on
  track 1 → overlap violation; the grain rides track 2.

## Story structure (9 frames, ~51s)

1. Hook — "¿Sabías que tu celular Android puede ser tu programador?" (kinetic type)
2. El mito — expensive setup struck through, "No es cierto." (kinetic type + strike)
3. La idea — orbit: Tú + celular + computador + SSH + modelo barato → "Ya tienes equipo"
4. Termux — phone mockup, `pkg install termux` types; dashed "TU FOTO AQUÍ" placeholder
5. SSH — lateral pan phone→computer, lavender bridge draws, SSH pill, "Puente"
6. OpenCode — work log: OpenCode Go + DeepSeek Flash, status swaps, check rows
7. Ya trabaja — prompt types "Diseña una presentación" → DISEÑA/PROGRAMA/CORRIGE
8. Cómo se hizo — typewriter meta-line: web templates + HTML, "sin programas pesados"
9. CTA — "Instalas. Conectas. Pides." → "Tú también puedes." (final frame, settle exit)

Frames 4 and 7 carry a dashed **"TU FOTO AQUÍ"** placeholder so the user can paste real
photos/videos of their Termux and dictation workflow later.

## Notes for future runs

- The brief asked for a "beautiful HTML" look; Capsule delivered it with zero external assets
  (all CSS/SVG). The user explicitly wanted to avoid Open Design (too heavy) — web-searched
  template inspiration became frame 8's "plantillas web + HTML" beat.
- Duration landed at 50.7s (voice-driven) vs the ~75s expectation; updated STORYBOARD
  `duration:` to match the real cut.
- Captions skipped: Kokoro emits no word timestamps; `captions.mjs` needs them.
