# ag-05 — Full-stack producer (DeepSeek V4 Pro, + FEEDBACK)

You produce a complete episode about e025-hyperliquid-candle-tails, end-to-end:
pick, run live, narrate reactively, capture, assemble, publish kit. **This is
the FEEDBACK arm of a 3-way comparison** (Flash E02 / Pro control ag-04 / Pro
+ feedback ag-05). Same experiment, same voice, same model as ag-04 — the ONLY
difference is the `## Feedback` section below, which you MUST apply rigorously.

## Model

`opencode -m opencode-go/deepseek-v4-pro`. Vision for reviewing frames:
`opencode-go/mimo-v2.5`.

## Episode assignment (fixed, do not change)

- **Experiment**: `../../e025-hyperliquid-candle-tails/` — the candle tail
  analysis. Read its `EXECUTIVE_SUMMARY.md` and `STRATEGY.md` first.
- **Topic**: the whole e025 story, explained clearly — what we asked, the 15
  agents, the honest nulls, the ONE edge that survived fees (daily crash
  reversion: crash OR low-volume-down, +0.55%/trade net, 312 OOS trades),
  the fees filter lesson, and the live paper monitor.
- **Voice**: **Alnilam** (kie-tts.sh `--voice Alnilam`) for ALL narration —
  identical in both comparison agents.
- **Format**: 16:9 long-form, English.
- **Notify when done**: `../../e000-fundamentals/bin/notify.sh done "E03 (Pro + feedback) episode ready" --file e023-build-in-public/ag-05-pro-feedback/output/episode.mp4`

## Feedback — E02 review (apply RIGOROUSLY, non-negotiable)

The E02 episode (same experiment, DeepSeek Flash) was reviewed by the user
(a complete beginner). These are the required improvements:

1. **Explanations — assume almost-zero knowledge.**
   - Define EVERY term the first time it appears — sigma, fat tail, kurtosis,
     out-of-sample, drawdown, funding, event study — in ONE plain sentence
     plus a real-world analogy ("a 3-sigma day is so rare it happens about
     once in a thousand days — like rolling a specific number twice").
   - Build incrementally: one concept → one example with REAL numbers from
     the experiment → then move on.
   - Keep sentences short. If one needs two clauses, split it.
   - The viewer must be able to follow WITHOUT pausing — if you ever think
     "they might get lost here," re-explain from scratch.

2. **Visual support — more variety, less text.**
   - At most 1/3 of screens may be pure-text slides. The rest MUST be real
     captures: terminal runs, the actual e025 charts (histograms,
     event-path curves, edge ledger, equity curves), the live paper monitor,
     and simple hand-drawn-style diagrams.
   - On every chart, add a large high-contrast CALL-OUT of the key number
     near the relevant feature (e.g. "+0.55% net per trade" next to the
     edge ledger row, or "kurtosis 13" on the histogram).
   - Reserve the bottom ~25% of the frame for subtitles: ALL slide/chart
     content lives in the top 75%. Never let slide text sit where subtitles
     will appear.
   - One idea per screen, big and centered (E01 rules still apply).

3. **Subtitles — TikTok / social style.**
   - 2-4 words per subtitle chunk, synchronized word-level to the narration.
   - Large font (≥ 34px), bold, high contrast: white text with strong black
     outline, always in the reserved bottom strip.
   - Highlight the key word of each chunk (color or extra emphasis) so the
     eye catches the important word.
   - One subtitle at a time, readable in a single glance.

## Per-episode sequence

1. **Plan** — write `output/episode-brief.md`: one-paragraph summary, hook, story arc, 3-6 key moments the camera must capture, honest angle. A map, not a script — you narrate live.
2. **Run live** — execute the experiment for real. Interact in the moment: run commands, open files, show errors, fix them on camera. Narrate in English as you go. Do NOT pre-execute and narrate over a recording.
3. **Capture** continuously while working.
4. **Assemble** — TTS → transcribe → build the video.
5. **Verify** — not black, audio present, narration matches screen (frames, ffprobe, OCR).
6. **Publish kit** — `output/publish-kit.md`.
7. **Log** — append a row to `output/episode-log.csv`.

## Production pipeline

Follow the fundamentals video pipeline. Capture 16:9 (1920x1080).

**Design the capture for the narration, NOT the other way around.** One idea per screen, large and readable; voiceover lines first, then a screen per line; results readable ~8-10s.

**TTS voiceover**: the ENTIRE narration in ONE pass or a few consecutive chunks with identical params and consistent silence; never many independent pieces blind-concatenated. Normalize silence before concatenating. Voice = Alnilam.

**Capture failure = episode failure, not a patch.** If the capture is broken, STOP and RE-CAPTURE with a corrected design. Verify capture end-to-end BEFORE generating any TTS.

- **Capture**: wf-recorder on your headless sway display. Verify with ffprobe.
- **TTS**: KIE Gemini TTS (`../../e019-kie-image-api/ag-01/bin/kie-tts.sh --voice Alnilam`). Fallback: edge-tts `en-US-JennyNeural`. English. Never espeak-ng.
- **Transcribe**: Deepgram fallback `bin/transcribe_cloud.py` (nova-3, word timestamps) if Parakeet is dead (venv likely wiped). Audio must be mono.
- **Assemble**: ffmpeg composition, TikTok-style subtitles (per the Feedback section), VAAPI encode (final MUST be h264_vaapi via `bin/encode_vaapi.sh`).
- **metadata.json**: hardware, software, cloud, narration, timestamps.

## Pitfalls (baseline knowledge, E01/E02)

- Reactive rule is absolute. No scripted narration over a recording.
- Human pacing: don't flash actions faster than a viewer can read.
- Honest failures are the channel's value.
- Verify every claim on screen. Trust nothing the tools output.
- Sway socket: `/run/user/1000/sway-ipc.1000.240699.sock` (check `ls /run/user/$(id -u)/sway-*`).
- HEADLESS-3 defaults to 608x1080 — resize to 1920x1080 with `swaymsg output HEADLESS-3 resolution 1920x1080`.
- wf-recorder keeps recording after the driver exits (black tail) — kill recorder by PID when the foot process disappears.
- This model can't read images: verify frames via OCR (`tesseract frame.png -`) + pixel-average checks; encoder tag via `ffprobe -show_entries stream_tags=encoder`.

## Parallel safety

You own **HEADLESS-3**. Create it if missing, verify free, record ONLY it. Never touch another display (ag-01 → HEADLESS-1, ag-04 → HEADLESS-2). Before/after capture run `pgrep -a wf-recorder`; kill orphans by exact PID only. Never `pkill wf-recorder`.

## Self-command

- Every blocking command runs in background: `> /dev/null 2>&1 &`
- After each command, self-wake: `tmux send-keys -t 23-5 "check status" Enter`
- Never leave a command without a timeout or self-wake.

## Inherits

- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — video pipeline, GPU encoding, transcription, subtitles, preferred TTS voices
- [../AGENTS.md](../AGENTS.md) — channel scope, architecture, format
- [../../e019-kie-image-api/AGENTS.md](../../e019-kie-image-api/AGENTS.md) — KIE TTS usage
- [../../e025-hyperliquid-candle-tails/AGENTS.md](../../e025-hyperliquid-candle-tails/AGENTS.md) — the experiment
