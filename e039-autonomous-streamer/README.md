# e039-autonomous-streamer

End-to-end pipeline that produces and publishes a narrated video with no human in the loop, so content gets made while the user sleeps.

## Pipeline stages

1. **Topic** — read `queue.md` (user drops topics). If empty → fallback: daily trading recap from e021/e025/e035 data.
2. **Script** — agent writes a narration script (English narration files per repo convention).
3. **Visuals** — HyperFrames composition rendered to MP4 (h264_vaapi), reusing patterns from e018/e034.
4. **Voice** — Kokoro TTS via CHUTES_API_KEY; Fish Audio fallback.
5. **Assemble** — ffmpeg mux audio + render + subtitles.
6. **Publish** — v1: upload as VOD/Shorts. v2: live stream via OBS (Xvfb) + obs-websocket (:4455) RTMP.

## Status

- [x] Scaffold
- [ ] queue.md topic source
- [ ] Script generator stage
- [ ] Render stage wiring
- [ ] TTS stage
- [ ] Assembly + QC pass
- [ ] Publisher
- [ ] Cron scheduling

## Conventions

Follows [e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md). All files and code in English.
