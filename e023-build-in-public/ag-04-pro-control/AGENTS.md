# ag-04 — Full-stack producer (DeepSeek V4 Pro, CONTROL)

You produce a complete episode about e025-hyperliquid-candle-tails, end-to-end:
pick, run live, narrate reactively, capture, assemble, publish kit. **This is
the CONTROL of a 3-way comparison** (Flash E02 / Pro control / Pro + feedback).
You must follow ONLY the baseline instructions below — the feedback variant
(ag-05) gets extra instructions. Same experiment, same voice, same model as
ag-05: the ONLY difference between you and ag-05 is that they have feedback.

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
- **Notify when done**: `../../e000-fundamentals/bin/notify.sh done "E03 (Pro control) episode ready" --file e023-build-in-public/ag-04-pro-control/output/episode.mp4`

## Per-episode sequence

1. **Plan** — write `output/episode-brief.md`: one-paragraph summary, hook (1 sentence), story arc (intro/body/conclusion), 3-6 key moments the camera must capture, honest angle. A map, not a script — you narrate live.
2. **Run live** — execute the experiment for real. Interact with the system in the moment: run commands, open files, show errors, fix them on camera. Narrate in English as you go: what you're doing, why, what the output means, what you conclude. Do NOT pre-execute and narrate over a recording.
3. **Capture** continuously while working.
4. **Assemble** — TTS → transcribe → build the video.
5. **Verify** — not black, audio present, narration matches screen (extract frames, ffprobe, OCR).
6. **Publish kit** — `output/publish-kit.md`: title, description, chapters, tags, thumbnail prompt, upload checklist.
7. **Log** — append a row to `output/episode-log.csv`.

## Production pipeline

Follow the fundamentals video pipeline. Capture 16:9 (1920x1080).

**Design the capture for the narration, NOT the other way around.** Every on-screen moment must show ONE thing, large and readable, matching exactly what is said:

- One idea per screen. A screen full of small text + voiceover = nobody reads it.
- Use BIG text (foot font-size ≥ 24-28; slides ≥ 34px).
- Write the voiceover lines first, then design a screen for each line.
- After a result appears, leave it readable ~8-10s before moving on.

**TTS voiceover**: generate the ENTIRE narration in ONE pass or a few consecutive chunks with identical voice/scene/context params and consistent silence. NEVER generate in many independent pieces and blind-concat. Normalize silence before concatenating. Voice = Alnilam.

**Capture failure = episode failure, not a patch.** If the capture is broken, STOP and RE-CAPTURE with a corrected design. Verify the capture end-to-end BEFORE generating any TTS.

- **Capture**: wf-recorder on your headless sway display. Verify with ffprobe.
- **TTS**: KIE Gemini TTS (`../../e019-kie-image-api/ag-01/bin/kie-tts.sh --voice Alnilam`). Requires `KIE_API_KEY`. Fallback: edge-tts `en-US-JennyNeural`. English. Never espeak-ng.
- **Transcribe**: Deepgram fallback `bin/transcribe_cloud.py` (nova-3, word timestamps) if the Parakeet worker is dead (it likely is — venv wiped). Audio must be mono.
- **Assemble**: ffmpeg composition, TikTok-style subtitles (short chunks, bottom), VAAPI encode (final MUST be h264_vaapi via `bin/encode_vaapi.sh`).
- **metadata.json**: hardware, software, cloud, narration, timestamps.

## Pitfalls (baseline knowledge, E01/E02)

- Reactive rule is absolute. No scripted narration over a recording.
- Human pacing: don't flash actions faster than a viewer can read.
- The topic is DECIDED (above) and the capture designed around it.
- Honest failures are the channel's value.
- Verify every claim on screen. Trust nothing the tools output.
- Sway socket: `/run/user/1000/sway-ipc.1000.240699.sock` (check `ls /run/user/$(id -u)/sway-*`).
- HEADLESS-2 defaults to 608x1080 — resize to 1920x1080 with `swaymsg output HEADLESS-2 resolution 1920x1080`.
- wf-recorder keeps recording after the driver exits (long black tail) — kill the recorder by PID when the foot process disappears.
- This model can't read images: verify frames via OCR (`tesseract frame.png -`) + pixel-average checks; encoder tag via `ffprobe -show_entries stream_tags=encoder`.

## Parallel safety

You own **HEADLESS-2**. Create it if missing, verify it's free, record ONLY it. Never touch another display (ag-01 owns HEADLESS-1, ag-05 owns HEADLESS-3). Before/after capture run `pgrep -a wf-recorder`; kill orphans by exact PID only. Never `pkill wf-recorder`.

## Self-command

- Every blocking command runs in background: `> /dev/null 2>&1 &`
- After each command, self-wake: `tmux send-keys -t 23-4 "check status" Enter`
- Never leave a command without a timeout or self-wake.

## Inherits

- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — video pipeline, GPU encoding, transcription, subtitles, preferred TTS voices
- [../AGENTS.md](../AGENTS.md) — channel scope, architecture, format
- [../../e019-kie-image-api/AGENTS.md](../../e019-kie-image-api/AGENTS.md) — KIE TTS usage
- [../../e025-hyperliquid-candle-tails/AGENTS.md](../../e025-hyperliquid-candle-tails/AGENTS.md) — the experiment
