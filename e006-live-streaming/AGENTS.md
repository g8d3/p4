# e006 — Live streaming + replay buffer

**Goal**: Build a pipeline that simultaneously streams live AND records the last N seconds (replay buffer) on the same hardware, using a single VAAPI encoder.

**Status**: Design phase. Tools not yet installed or configured.

## Hardware

- **CPU**: AMD Ryzen 5 5625U (6C/12T)
- **GPU**: AMD Barcelo (iGPU, gfx903, 8 CU)
- **RAM**: 15 GB
- **GPU encoder**: VAAPI (`h264_vaapi`) — hardware encoding, 0% CPU
- **Driver**: Mesa radeonsi, DRM 3.57, kernel 6.8.0

## Current infrastructure (inherited from e003/e004/e005)

- Sway (wlroots) on AMD GPU with virtual displays
- wf-recorder + VAAPI for capture
- Xvfb as fallback (x11grab, ~5% CPU)
- edge-tts with Colombian voices (es-CO-SalomeNeural / es-CO-GonzaloNeural)
- OpenCode agents for automation

## Design decisions

### Single encoder, two outputs

Do NOT run two VAAPI encoder instances simultaneously. The Barcelo has limited encoding resources. Instead:

1. Capture frames once (wf-recorder or ffmpeg x11grab)
2. Encode once with VAAPI
3. Split output to two destinations using ffmpeg tee muxer

```
Display (Sway/Xvfb)
  → wf-recorder / ffmpeg capture
    → VAAPI encode (single pass)
      ├→ tee → RTMP stream (live)
      └→ tee → ring buffer (replay)
```

### Ring buffer: "last N seconds" mode

The replay buffer keeps the most recent N seconds of video in RAM and writes to disk on demand.

**RAM usage by config:**

| Config | Bitrate | RAM/second | 30s buffer | 60s buffer | 5min buffer |
|--------|---------|------------|------------|------------|-------------|
| 1080p30 CBR 4Mbps | 4 Mbps | 0.5 MB/s | 15 MB | 30 MB | 150 MB |
| 1080p60 CBR 6Mbps | 6 Mbps | 0.75 MB/s | 22 MB | 45 MB | 225 MB |
| 720p30 CBR 3Mbps | 3 Mbps | 0.375 MB/s | 11 MB | 22 MB | 112 MB |

With 15 GB RAM, even a 5-minute buffer at 1080p60 is trivial (225 MB).

### Recording vs streaming: key differences

| Aspect | Recording (off-line) | Streaming (live) |
|--------|---------------------|------------------|
| Bitrate | High (max quality) | Limited by upload bandwidth |
| Encoding profile | High (best compression) | Main/Baseline (compatibility) |
| Latency | Doesn't matter | < 2 seconds preferred |
| Network | Not required | Critical — drops = stream dies |
| Real-time | Not required | Mandatory — every frame has deadline |
| Failure | Re-record | Moment is lost |
| Tool | wf-recorder + ffmpeg | OBS Studio or ffmpeg + RTMP |

### Upload bandwidth requirements

| Quality | Min upload | Recommended |
|---------|-----------|-------------|
| 720p30 | 3 Mbps | 5 Mbps |
| 1080p30 | 5 Mbps | 8 Mbps |
| 1080p60 | 8 Mbps | 12 Mbps |

## Pipeline options

### Option A: ffmpeg tee muxer (CLI, full control)

```bash
# Capture from Xvfb display :99, encode with VAAPI, split to stream + ring buffer
ffmpeg -f x11grab -video_size 1920x1080 -framerate 30 -i :99.0 \
  -c:v h264_vaapi -b:v 6M -maxrate 6M -bufsize 12M \
  -f tee "[f=flv]rtmp://twitch.tv/live/KEY|[f=mp4]ring_buffer.mp4"
```

### Option B: OBS Studio (GUI, integrated replay buffer)

OBS has replay buffer built-in:
- Settings → Output → Streaming: RTMP config
- Settings → Output → Recording: Replay Buffer enabled
- Settings → Output → Replay Buffer: Maximum Replay Time (seconds)
- Uses VAAPI automatically if configured

### Option C: wf-recorder + separate RTMP push

```bash
# wf-recorder captures, pipes to ffmpeg for RTMP
wf-recorder -c h264_vaapi -f - | \
ffmpeg -i - -c:v copy -f flv rtmp://twitch.tv/live/KEY
```

## Open questions (to resolve before implementation)

1. **Which streaming platform?** Twitch, YouTube, self-hosted (Owncast)?
2. **Which capture method?** DMA-BUF (requires TTY/Sway) or x11grab (works from SSH)?
3. **Vertical or horizontal?** Current setup is vertical (608x1080) — streaming platforms prefer horizontal (1920x1080)
4. **Audio source?** edge-tts narration, microphone, system audio, or mix?
5. **Ring buffer trigger?** How does the agent/user trigger "save last N seconds"? (CLI command, hotkey, API)
6. **OBS or pure CLI?** OBS is easier but heavier; ffmpeg tee is lighter but requires manual setup

## TODO

- [ ] Decide platform and capture method
- [ ] Install OBS or configure ffmpeg tee pipeline
- [ ] Test single VAAPI encoder with dual output
- [ ] Implement ring buffer mechanism
- [ ] Test with agent narration (edge-tts + streaming)
- [ ] Benchmark: GPU load with stream + buffer simultaneously
- [ ] Document final working pipeline
- [ ] **Pain point**: measure concurrent agent capacity (proxy in p3)

## Inherits

- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, GPU encoding
- [../e003-wayland-migration/AGENTS.md](../e003-wayland-migration/AGENTS.md) — Wayland/Sway setup
- [../e004-agent-screencast/AGENTS.md](../e004-agent-screencast/AGENTS.md) — agent recording pipeline
- [../e005-gpu-browser-capture/AGENTS.md](../e005-gpu-browser-capture/AGENTS.md) — GPU capture with VAAPI
