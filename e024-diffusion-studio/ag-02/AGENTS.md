# ag-02 — Code tutorial: your first composition

Second agent for the Diffusion Studio experiment. ag-01 covered the setup,
exploration, benchmark, and a broad "what is it + honest verdict" demo. This
agent owns the follow-up video: a **hands-on code tutorial** that walks through
the JSX composition API and the `dapi mount → inspect → render` loop, using the
tool's own source as the subject.

## Model

`opencode -m opencode-go/deepseek-v4-flash` (priority 1).

## Mission

Produce one finished, verified 16:9 (1920×1080) video, `output/first-composition.mp4`,
a pre-generated composition video (not a live screen capture) that teaches a
viewer how to write and render their first Diffusion Studio composition.

Pipeline (fundamentals): script → KIE Gemini TTS → Parakeet transcription →
code-slide visuals → ffmpeg assembly → **final encode with h264_vaapi**
(`../../e023-build-in-public/bin/encode_vaapi.sh`), then verify + metadata.

The narration is written in `bin/script.md`. Visuals are rendered code slides
(HTML → headless Chrome PNGs, 1920×1080) plus any real `dapi node capture`
frames if the editor is up; otherwise slides alone are fine — the video must
still be self-contained and readable.

## Success criteria

- `output/first-composition.mp4`: 1920×1080, audio present, non-black readable
  frames, verified with ffprobe (encoder tag must contain `vaapi`).
- `output/metadata.json` lists hardware, software, cloud (KIE TTS), narration,
  timestamps, and every asset used.
- `bin/` holds the committed sources: `script.md`, the slide generator, and the
  assembly script, so the whole video is reproducible from the repo.

## Pitfalls (from ag-01, still true)

- Final encodes MUST go through `encode_vaapi.sh` (GPU h264_vaapi). Never
  `-c:v libx264` for the deliverable.
- KIE Gemini TTS truncates long requests (~106 s max) — split the narration into
  parts and concatenate with ffmpeg.
- Parakeet needs mono audio — convert with `ffmpeg -i in.mp3 -ac 1 out.mp3`
  before transcribing.
- `dapi node render` default AAC audio fails on this Chromium build; if you ever
  render via the editor, pass `"audio":{"codec":"opus"}`.
- The editor requires the Electron app over `/tmp/diffusion-studio.sock`; do not
  assume `dapi` works without it. For this video the editor render is optional,
  not a blocker.
- Verify every command's output — never trust a 0-byte render or an empty frame.

## Learnings (2026-08-12)

- **Parakeet is broken on this machine** (venv in `/tmp` wiped, `nemo_toolkit`
  won't install on Python 3.11). Timing was computed from measured KIE TTS part
  durations + paragraph word counts instead of a Parakeet transcription. Cloud
  alternatives researched in
  [`../../e018-hyprframes-browser-video/ag-02/bin/CLOUD-ASR.md`](../../e018-hyprframes-browser-video/ag-02/bin/CLOUD-ASR.md).
- **ffmpeg OOM trap (cost us a killed process)**: feeding PNGs straight into the
  concat demuxer (`-f concat` list of images) with an `fps=25` filter ballooned
  ffmpeg to ~14.6 GB RSS and the OOM killer killed it. Fix: render each slide to
  a short H.264 segment (`-loop 1 -framerate 25 -i x.png -t <dur>`), then
  `-f concat -c copy` the segments. Memory-safe and fast.
- **encoder tag was a false negative, now fixed**: `ffprobe -show_entries
  stream=encoder` returns empty because the encoder name is a stream *tag*, not
  a direct stream field. Use `-show_entries stream_tags=encoder` — it correctly
  reports `Lavc60.31.102 h264_vaapi`. `encode_vaapi.sh` and the fundamentals
  docs were fixed accordingly.

## Self-command

- Every blocking command runs in background: `> /dev/null 2>&1 &`
- After each command, self-wake:
  `tmux send-keys -t <window> "check status" Enter` (Enter is required)
- Never leave a command without a timeout or self-wake.

## Inherits

- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — video
  pipeline, GPU/VAAPI rule, command rules, background + self-wake
- [../AGENTS.md](../AGENTS.md) — experiment scope, repo layout, core workflow
- [../ag-01/AGENTS.md](../ag-01/AGENTS.md) — setup path, dapi command surface,
  encoder reality, verified pitfalls
- [../../e019-kie-image-api/AGENTS.md](../../e019-kie-image-api/AGENTS.md) — KIE
  TTS usage
- [../../e018-hyprframes-browser-video/AGENTS.md](../../e018-hyprframes-browser-video/AGENTS.md) —
  Parakeet transcription
