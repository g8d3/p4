# e010-more-videos

## Inherits
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md)

## Goal

Produce many videos (even imperfect ones) using multiple agents working simultaneously. Agents use Mimo (has vision) to self-review and iterate on their own video output.

## Structure

```
ag-00/    Infrastructure: pdw, record.sh, launch-agents.sh, sway-headless.conf, shared output/
ag-01/    Virtual display + recording pipeline (Xvfb + Sway + ffmpeg)
ag-02/    Resource monitoring (CPU, GPU, tokens/sec comparison)
ag-03/    TTS/ASR with Xiaomi MIMO + video narration
ag-04/    Documentation: GUIA.md (unified plan), PENDIENTES.md (future improvements), TODO.md
ag-05/    Terminal demo: interactive pdw walkthrough + 2 narration versions (self + commentators)
ag-06/    Browser demo: GitHub/Trendshift/HuggingFace trends + 2 narration versions (self + commentators)
```

## Model

All agents use `opencode-go/mimo-v2.5` (has vision for self-review).

## Infrastructure

- Wayland virtual displays (Sway headless, 608x1080 vertical) — no Xvfb
- DMA buffer for efficiency
- **Shared recording script**: `bin/record.sh <name> [duration]` — one-command recording. All agents should use this instead of writing custom recording pipelines.

## Shared tools

| Tool | Usage | Description |
|------|-------|-------------|
| `ag-00/bin/record.sh` | `../ag-00/bin/record.sh <name> <output> <duration>` | Record a specific virtual display. Creates output if missing. Multiple recordings on different outputs run simultaneously. Example: `../ag-00/bin/record.sh demo HEADLESS-1 30` |
| `ag-00/bin/pdw` | `../ag-00/bin/pdw <command>` | Full display manager: init, ds, w, rec, vnc, clean |
- DMA buffer for efficiency
- ffmpeg with VAAPI encoding
- Xiaomi MIMO API for TTS/ASR
- Timestamp recording for fast-motion narration

## Core directive: never stop

This experiment has one rule above all others: **agents produce videos forever**.

- Do NOT stop after one video. Each video is an iteration.
- After each video: review output → review process → update your AGENTS.md → produce the next video with improvements.
- Your folder should fill with videos over time. Each one should be better than the last.
- The user will review from newest to oldest to see the improvement trajectory.

## Instructions from transcription

1. Launch 3 agents simultaneously doing diverse tasks
2. Agents should produce videos using the pipeline
3. Agents should self-review their videos (Mimo has vision)
4. Iterate forever — never stop after one video
5. Fast-motion for boring/failed steps
6. Human-like narration (not just reading timestamps)

## Video quality rules (read this to every agent)

Every agent must read and follow these rules before recording:

1. **Be reactive**: You are a human teacher. Interact with the system live. Think, type, read output, react, explain. Do NOT pre-script.
2. **Narrate with purpose**: Match your words to what's on screen. Explain WHY, not just WHAT.
3. **Pace for humans**: Slow down. Let the viewer read and process. Machine speed = unwatchable.
4. **Structure your video**: Intro (what and why) → Body (live work with live thinking) → Conclusion (findings + call to action / cliffhanger).
5. **Synchronize**: What you say must match what's shown. If you show htop, explain the CPU column.
6. **Audio**: Leave silence when TTS/demo audio plays. Don't talk over it.
