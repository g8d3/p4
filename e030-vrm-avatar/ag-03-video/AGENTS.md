# ag-03 — Talking-avatar video production

Produce a 30-60 s vertical talking-avatar video by driving the three.js/three-vrm
avatar with TTS narration and capturing it in real time.

## Scope

1. **Narration** (`e019-kie-image-api/ag-01/bin/kie-tts.sh`, approved voice).
   Topic: the VRM avatar itself / what you built (entertaining + educational +
   quantitative style). Vertical.
2. **Transcribe** (`e018-hyprframes-browser-video/ag-02/bin/transcribe.sh`) →
   `.srt` + `.txt` + word timestamps.
3. **Lip-sync timeline**: ffmpeg decode to mono PCM, windowed RMS (~80-100 ms)
   → `mouth.json` `[[t_ms, weight],…]` per scene.
4. **Performance script**: expression/idle cues + `speak` timed to narration
   (format in ag-02 AGENTS.md). Drive either client via the `avatar` CLI
   (ag-02's) or direct `/cmd`.
5. **Capture**: sway headless 608x1080 + wf-recorder (`--no-dmabuf
   --no-damage -c libx264`). Sway is NOT currently running — start it per e000
   fundamentals. Play the performance while capturing; verify frames not black
   and audio present.
6. **Encode**: `e023-build-in-public/bin/encode_vaapi.sh` → final video. Verify
   `ffprobe` shows `vaapi` in `stream_tags=encoder`. **Never libx264 for the
   final file.**
7. **`output/metadata.json`** per e000 fundamentals (hardware, software, cloud,
   narration model/voice, timestamps).
8. **Self-review**: extract 3-4 frames, review with your own vision capability
   (glm-4.7 has vision) — character visible, mouth moves during speech, colors
   correct. Iterate if wrong.

## Success criteria

- Final video 608x1080, 30-60 s, audible narration, mouth visibly moves with
  speech, VAAPI encoder tag, `metadata.json` complete.
- The performance was driven programmatically via CLI/API — not manual clicks.

## Self-command
All long running work (capture, encode, TTS, transcribe, seedream) in
background with self-wake context; always `Enter`:
`tmux send-keys -t 30-3 "Self-wake: <pid> <step> <what to check> <next>" Enter`

## Window discipline (no cross-talk)
- Your window is **30-3** and it is the ONLY tmux window you may operate on.
- NEVER run `tmux send-keys`, `tmux kill-window`, `tmux rename-window`, or
  `tmux new-window` targeting any other window or session. Other agents live in
  `a0`, `a1`, `30-1` — never touch them.
- NEVER pkill anything. Kill only your own PIDs. Never kill/restart another
  agent's node/chrome (avatar server is a shared resource — you may poll it).
- When you need something from another agent, use `notify.sh ... --ask` (goes
  to the orchestrator inbox). Never message agents directly.

## Model
`zai-coding-plan/glm-4.7`. If the provider is out of credits, request
direction via `notify.sh … --ask` — do not silently downgrade.

## Command execution
- `timeout` every command; background servers/captures.
- Verify each pipeline stage before proceeding (audio exists, transcript has
  words, capture not black, encoder tag = vaapi).

## Pitfalls
- The avatar client must be running and healthy BEFORE capture starts
  (`avatar inspect`). If the server/client is not ready, use that time to do
  TTS + transcription + timeline work, then check again.
- wf-recorder from headless sway: `--no-dmabuf --no-damage` required.
- Don't start capture before the audio/server is verified — a black-avatar
  video wastes a real-time capture slot.
- Final encode MUST be VAAPI; check the encoder tag, not just the codec.

## Output
`output/narration.mp3`, `output/transcript.*`, `output/mouth.json`,
`output/performance.json`, `output/capture.mp4`, `output/final.mp4`,
`output/metadata.json`, `done.txt` + `notify.sh done`.

## Inherits
- [../../../e000-fundamentals/AGENTS.md](../../../e000-fundamentals/AGENTS.md)
- [../AGENTS.md](../AGENTS.md)