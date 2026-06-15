# e004 — Agent screencast

**Goal**: Produce publishable videos by recording agents working in real-time: browsing, researching, testing tools, and narrating their process. No scripts, no avatars — the agent's live workflow is the content.

## Core pipeline

```
Agent works (browses, codes, tests)
  → wf-recorder captures GPU-direct
  → TTS narrates agent's thoughts in real-time
  → VAAPI encodes to MP4 (zero CPU)
  → Agent reviews own video with Mimo 2.5 (vision)
```

## Principles

- **Exploratory, not scripted**: agents react to what they find, narrate spontaneously
- **Self-review**: agents watch their own recording and critique/fix issues
- **Parallel discovery**: multiple agents research different topics simultaneously
- **Modern sources**: X.com, Hugging Face, GitHub for finding latest tools
- **GPU-only pipeline**: wf-recorder + VAAPI, no CPU encoding

## Agents

- **ag-01**: TTS researcher — explore X.com/HF for the best modern TTS, test them, record and narrate the process
- **ag-02**: Visual style researcher — explore video trends, image generation, templates; record findings
- **ag-03**: Render log aggregator — collects metrics from all agents into a unified CSV, analyzes efficiency
- **ag-04**: FileX CSV/table renderer — add CSV table rendering and more inline file types to filex server
- **ag-05**: Kokoro TTS explorer — figure out Chutes API for Kokoro TTS, document in fundamentals

## Metrics

All agents append render data to `ag-03/render-log.csv`:
```csv
timestamp,agent_id,experiment,step,duration_sec,gpu_busy_pct,output_fps,file_size_mb,resolution,display_type,display_id,notes
```

## Infrastructure (shared)

- Sway running with DRM (wayland-1)
- wf-recorder for capture
- VAAPI for encode
- Browser (epiphany) with GPU acceleration for web research
