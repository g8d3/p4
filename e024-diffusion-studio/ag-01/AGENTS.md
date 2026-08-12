# ag-01 — Setup, exploration & composition

Full-stack agent for the Diffusion Studio experiment: set up the editor from
`../upstream/`, explore the `dapi` CLI until the toolset is understood, write
TSX compositions, render real videos, and benchmark against the p4 ffmpeg/VAAPI
pipeline. You are the only agent here — you own everything end to end, so keep
notes as you go (`output/exploration.md`) or the next run loses your context.

## Model

`opencode -m opencode-go/deepseek-v4-flash` (priority 1).

## Mission

1. **Install** — `npm install` in `../upstream/`, copy `.env.example` → `.env`,
   and get the editor running. Try `npm run dev:web` first (browser mode,
   fewer moving parts than Electron). Link `dapi` on PATH via
   `npm run symlink:create --workspace=@diffusionstudio/cli`.
2. **Verify** — `dapi open -b` (headless) or with a display, then `dapi
   whoami`, `dapi context`, `dapi models`. Confirm the CLI actually talks to
   the app over the local socket before trusting any output.
3. **Explore** — read `../upstream/reference/` (every command) and
   `../upstream/examples/` (runnable compositions). Try the examples:
   `dapi mount ../upstream/examples/01-basics.tsx`, `dapi node tree`, `dapi
   node capture`, `dapi node render -o <out>.mp4`.
4. **Compose** — write your own compositions in `bin/` (TSX modules), e.g.:
   - A title/text scene from a local TTS narration (KIE Gemini TTS via
     `../../e019-kie-image-api/ag-01/bin/kie-tts.sh`, or edge-tts fallback).
   - A real-footage scene using media produced elsewhere in p4 (check
     `../../e018-hyprframes-browser-video/`, `../../e010-more-videos/` for
     existing captures you can import as assets).
   - A captions/subtitles scene driven by a Parakeet `.srt`/transcript
     (`../../e018-hyprframes-browser-video/ag-02/bin/transcribe.sh`).
5. **Render & verify** — `dapi mount <comp>.tsx`, `dapi node render -o
   output/<name>.mp4`. Verify every output with ffprobe: resolution matches
   the composition, duration is sane, audio present, no black frames.
6. **Benchmark** — compare against the p4 ffmpeg composition pipeline: encode
   speed, quality, control, effort. Write the comparison to
   `output/benchmark.md` with real numbers (file sizes, encode times, encoder
   tags, commands used).

## Success criteria

- `dapi` responds on the linked PATH and `dapi node render` produces a real
  `.mp4` on disk (verify with `ffprobe` — resolution, duration, no black).
- `output/exploration.md` exists and answers: how to start the app, which
  commands are agent-critical, what needs the hosted backend vs works offline,
  and how `dapi node render` encodes (codec, hardware) vs the p4 VAAPI rule.
- At least two rendered videos in `output/` (one pure-composition, one with
  p4-generated audio/footage), each verified with ffprobe and with a frame
  extracted to confirm non-black content.
- `output/benchmark.md` states, with evidence, whether `dapi node render`
  should be adopted, adapted, or ignored by the p4 pipeline — and why.

## Pitfalls (check before assuming)

- The app may need `apps/web/.env` (Supabase + API keys) or it won't run —
  the example file exists in the repo, copy it.
- `dapi` talks to a **running app** over a local socket. Commands fail if the
  app isn't up. Check `dapi logs` and the socket before debugging the CLI.
- `dapi node render` renders in the browser engine (WebCodecs) — verify the
  encoder tag with ffprobe before comparing it to the p4 h264_vaapi rule.
- `npm install` on 5 workspaces can take minutes and print warnings. Background
  it with a self-wake instead of blocking.
- The repo is a moving target (v0.132.0); if a documented command has no
  reference file or differs from `reference/`, trust the live `dapi --help`.
- The FINAL p4 deliverable rule still applies if you assemble a final video
  with ffmpeg: encode with h264_vaapi (`../../e023-build-in-public/bin/encode_vaapi.sh`),
  verify the encoder tag. `dapi node render`'s own encoder is a separate
  question — report what it produces, don't silently hand it to the pipeline.
- Generative assets (`generate.*`) may hit the hosted API and cost
  credits/require an account. Prefer local media for the core benchmark; use
  `generate.*` only as an exploration add-on.
- Parakeet needs mono audio; transcribe first, then reference the transcript
  in your composition.
- Composition sources are the deliverable — commit them in `bin/` with a
  short README if useful.

## Self-command

- Every blocking command runs in background: `> /dev/null 2>&1 &`
- After each command, self-wake:
  `tmux send-keys -t <window> "check status" Enter` (Enter is required)
- Never leave a command without a timeout or self-wake.

## Inherits

- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles,
  command rules, background + self-wake pattern, GPU/VAAPI encoding, video pipeline
- [../AGENTS.md](../AGENTS.md) — experiment scope, repo layout, core workflow
- [../../e019-kie-image-api/AGENTS.md](../../e019-kie-image-api/AGENTS.md) — KIE TTS usage
- [../../e018-hyprframes-browser-video/AGENTS.md](../../e018-hyprframes-browser-video/AGENTS.md) — Parakeet transcription
