# ag-02 — Compositions & integration

Write Diffusion Studio TSX compositions and produce real videos, integrating
the p4 asset stack (KIE TTS narration, Parakeet transcription, real captures)
where it makes sense. Your goal is to prove or disprove Diffusion Studio as a
p4 production tool, with evidence.

## Model

`opencode -m opencode-go/deepseek-v4-flash` (priority 1).

## Mission

1. **Learn the markup** — read `../upstream/reference/jsx/` (elements,
   timing, paints, generative assets, captions) and `../upstream/examples/`.
   The markup is pseudo-SVG with the editor's own tags.
2. **Compose** — write your own compositions in `bin/` (TSX modules), e.g.:
   - A title/text scene from a local TTS narration (KIE Gemini TTS via
     `../../e019-kie-image-api/ag-01/bin/kie-tts.sh`, or edge-tts fallback).
   - A real-footage scene using media produced elsewhere in p4 (check
     `../../e018-hyprframes-browser-video/`, `../../e010-more-videos/` for
     existing captures you can import as assets).
   - A captions/subtitles scene driven by a Parakeet `.srt`/transcript
     (`../../e018-hyprframes-browser-video/ag-02/bin/transcribe.sh`).
3. **Render & verify** — `dapi mount <comp>.tsx`, `dapi node render -o
   output/<name>.mp4`. Verify every output with ffprobe: resolution matches
   the composition, duration is sane, audio present, no black frames.
4. **Benchmark** — compare against the p4 ffmpeg composition pipeline: encode
   speed, quality, control, effort. Write the comparison to
   `output/benchmark.md` with real numbers (file sizes, encode times, encoder
   tags, commands used).

## Success criteria

- At least two rendered videos in `output/` (one pure-composition, one with
  p4-generated audio/footage), each verified with ffprobe and with a frame
  extracted to confirm non-black content.
- `output/benchmark.md` states, with evidence, whether `dapi node render`
  should be adopted, adapted, or ignored by the p4 pipeline — and why.

## Pitfalls (check before assuming)

- `dapi` needs a running app (see ag-01). If the app is down, commands fail —
  restart it, don't debug the CLI.
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
  short comment-free README if useful.

## Self-command

- Every blocking command runs in background: `> /dev/null 2>&1 &`
- After each command, self-wake:
  `tmux send-keys -t <window> "check status" Enter` (Enter is required)
- Never leave a command without a timeout or self-wake.

## Inherits

- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — video
  pipeline, TTS, transcription, GPU/VAAPI encoding, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope, repo layout, core workflow
- [../../e019-kie-image-api/AGENTS.md](../../e019-kie-image-api/AGENTS.md) — KIE TTS usage
- [../../e018-hyprframes-browser-video/AGENTS.md](../../e018-hyprframes-browser-video/AGENTS.md) — Parakeet transcription
