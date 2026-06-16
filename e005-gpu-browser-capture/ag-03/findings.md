# AI Explorations — June 16, 2026 (Session 3)

## Topics Explored

1. **GitHub Trending AI Repos** — Browsing latest open-source AI projects with xdotool interaction
2. **xdotool Browser Automation** — Scrolling pages, switching tabs via keyboard simulation
3. **Resource Monitoring** — GPU busy%, CPU%, disk writes logged per-second to metrics.csv
4. **Pipeline Logging** — Every step logged to pipeline-log.csv with timestamps and status

## Pipeline Enhancements

- **Browser motion**: xdotool loop scrolls pages and switches tabs during 30s recording
- **Resource monitor**: Background loop logs per-second GPU/CPU/disk telemetry
- **Pipeline logging**: All 6 steps (xvfb, browser, narration, recording, merge, verify) logged with run ID
- **Merge**: Same `-movflags +faststart` web-optimized output

## Key Takeaway

Combining xdotool interaction with VAAPI recording and resource monitoring produces a complete, verifiable autonomous content capture pipeline with full telemetry.
