# e007 — Agent self-documentation

**Goal**: Produce publishable videos from two sources: (1) an agent recording itself while working, and (2) converting human-agent interactions into video content.

## Core principle

The pipeline is the same for both agents:

```
Data source → Structured log → Narration → Composition → Video
```

The intelligence is in post-production, not in the recording. The agent just works and logs.

## Agents

- **ag-01**: Self-recording agent — records its own screen while researching/working, logs actions with timestamps, produces video with fast-motion for boring parts
- **ag-02**: Interaction-to-video agent — takes chat logs (human + agent conversations), extracts key moments, produces narrative video
- **ag-03**: Agent optimizer — reviews and optimizes AGENTS.md files, measures thinking efficiency (thinking ratio, time-to-first-action, plan iterations)

## Shared infrastructure

- **Display**: Sway + AMD virtual displays (DMA-BUF, 0% CPU capture)
- **Capture**: wf-recorder + h264_vaapi
- **Format**: 608x1080 vertical (TikTok)
- **TTS**: edge-tts, es-CO-SalomeNeural / es-CO-GonzaloNeural
- **Encoding**: VAAPI hardware, 0% CPU
- **Post-production**: ffmpeg (cuts, speed changes, overlays, composition)
- **Data viz**: matplotlib + pandas (tables, graphs)

## Recording pipeline (ag-01)

```
Agent works (browses, codes, tests)
  → wf-recorder captures continuously (DMA-BUF, 0% CPU)
  → Agent writes to log.csv: {timestamp, action, opinion, finding}
  → Agent marks segments: {start, end, type: normal|fast}
  → Post-production script:
      1. Read log
      2. Identify interesting vs boring segments
      3. Apply fast motion to boring parts
      4. Generate narration from log (edge-tts)
      5. Compose: video + speed changes + narration + overlays
      6. Output: final.mp4
```

## Interaction pipeline (ag-02)

```
Chat log (from opencode, terminal, or other source)
  → Parser extracts: {timestamp, speaker, message, context}
  → Structure into narrative arc: intro → development → conclusion
  → Generate narration (edge-tts)
  → Select relevant visual moments (if screen recording exists)
  → Compose: visuals + narration + text overlays
  → Output: final.mp4
```

## Video format

| Property | Value |
|----------|-------|
| Resolution | 608x1080 (9:16 vertical) |
| FPS | 30 |
| Codec | h264_vaapi |
| Bitrate | 4-6 Mbps |
| Audio | AAC 128kbps (from edge-tts) |

## Log format (ag-01)

```csv
timestamp,action,opinion,finding,segment_type
2026-06-17T10:00:00,start_recording,,,"normal"
2026-06-17T10:00:15,navigate_huggingface,,"Found Piper TTS","normal"
2026-06-17T10:00:45,compare_pricing,,"Piper is free, local","normal"
2026-06-17T10:01:30,scroll_docs,,,"fast"
2026-06-17T10:02:00,install_piper,,"Testing installation","normal"
```

## Post-production rules

1. **Fast motion**: segments marked "fast" → 4x-8x speed
2. **Normal**: segments marked "normal" → 1x speed
3. **Narration**: generated AFTER recording, from log content
4. **Overlays**: tables/graphs inserted at specific timestamps
5. **Transitions**: simple cuts between segments (no fancy transitions)

## TODO

- [ ] Set up Sway + virtual displays for DMA-BUF capture
- [ ] Design log.csv schema
- [ ] Build post-production script (ffmpeg composition)
- [ ] Test ag-01: agent records itself researching TTS
- [ ] Test ag-02: parse this chat log → video
- [ ] Benchmark: GPU/CPU/disk during recording + post
- [ ] **Pain point**: measure concurrent agent capacity before launching ag-01 + ag-02 in parallel

## Inherits

- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, GPU encoding
- [../e004-agent-screencast/AGENTS.md](../e004-agent-screencast/AGENTS.md) — agent recording pipeline
- [../e005-gpu-browser-capture/AGENTS.md](../e005-gpu-browser-capture/AGENTS.md) — GPU capture with VAAPI
- [../e006-live-streaming/AGENTS.md](../e006-live-streaming/AGENTS.md) — streaming infrastructure
