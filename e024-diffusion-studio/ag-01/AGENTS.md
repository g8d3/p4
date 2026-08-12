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
7. **Demo video (the final deliverable)** — a video **about the tool itself**:
   - **Topic**: "Diffusion Studio — the video editor your coding agents can
     drive." What it is, the `dapi` CLI workflow, compositions as TSX, and an
     honest comparison with p4's ffmpeg/VAAPI pipeline.
   - **Aspect ratio**: 16:9 (1920×1080). **Duration**: not predefined — it
     results from the narration transcription.
   - **Pipeline**: composition video (pre-generated). Write the script, TTS
     it (KIE Gemini TTS via
     `../../e019-kie-image-api/ag-01/bin/kie-tts.sh`), transcribe (Parakeet),
     then assemble the scenes as TSX compositions (`dapi mount` + `dapi node
     render`) — the subject and the tool are the same. Use `generate.*` assets
     and/or real p4 media in the scenes.
   - **Verify**: ffprobe (1920×1080, audio present, encoder tag) + extracted
     frames with readable, non-black content. Write `output/metadata.json`
     (per fundamentals) and commit the composition sources in `bin/`.

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
- `output/demo.mp4` — the final demo video about the tool itself: 1920×1080,
  audio present, non-black readable frames, verified with ffprobe +
  extracted frames. `output/metadata.json` written per fundamentals.

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

## Learnings (2026-08-12, first session)

- **Render encoder is software H.264 (OpenH264), not VAAPI** — and ffprobe
  reports no encoder tag. Default AAC audio FAILS (`encoder config not
  supported`); always pass `"audio":{"codec":"opus"}`. ~100 FPS at 1080p.
- `dapi` talks to the **Electron desktop app** over `/tmp/diffusion-studio.sock`
  — browser-only `dev:web` is not enough. Launch Electron headless on a sway
  Wayland display; `dapi open -b` needs a `diffusion-studio` binary we don't
  have, so launch electron directly.
- Render returns `{path}` + exit 0 even when the file is 0 bytes — always
  verify with ffprobe. A hung render wedges the app; restart all electron pids.
- `npm install` needs `npm config set allow-git all` (npm 12), then approve
  esbuild's install script and run electron's `install.js` manually.
- `dapi fonts` is macOS only. On Linux only `Inter` is available.
- `pkill -f electron` matches the agent's own shell — use exact PIDs.
- The p4 GPU rule still applies for final delivery: `encode_vaapi.sh` accepts a
  dapi mp4 unchanged (verified). Verdict in `output/benchmark.md`:
  **adopt the editor for authoring, keep h264_vaapi for encoding.**

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
