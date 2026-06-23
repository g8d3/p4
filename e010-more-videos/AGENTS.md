# e010-more-videos

## Inherits
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md)

## Goal

Produce many videos (even imperfect ones) using multiple agents working simultaneously. Agents use Mimo (has vision) to self-review and iterate on their own video output.

## Structure

```
ag-01/    Virtual display + recording pipeline (Xvfb + Sway + ffmpeg)
ag-02/    Resource monitoring (CPU, GPU, tokens/sec comparison)
ag-03/    TTS/ASR with Xiaomi MIMO + video narration
```

## Model

All agents use `opencode-go/mimo-v2.5` (has vision for self-review).

## Infrastructure

- Xvfb virtual displays (vertical 608x1080)
- Wayland (Sway) as window manager
- DMA buffer for efficiency
- ffmpeg with VAAPI encoding
- Xiaomi MIMO API for TTS/ASR
- Timestamp recording for fast-motion narration

## Instructions from transcription

1. Launch 3 agents simultaneously doing diverse tasks
2. Agents should produce videos using the pipeline
3. Agents should self-review their videos (Mimo has vision)
4. Iterate until acceptable quality
5. Fast-motion for boring/failed steps
6. Human-like narration (not just reading timestamps)
