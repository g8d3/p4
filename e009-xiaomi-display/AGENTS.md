# e009-xiaomi-display

Display virtual vertical con VNC web + audio streaming + API Xiaomi MIMO (TTS/ASR).

## Inherits
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md)

## Estructura

```
ag-01/    Display virtual (Xvfb) + VNC + Xiaomi TTS/ASR web       [legacy]
ag-02/    Agent Studio specs                                       [specs]
ag-03/    Wayland virtual display + noVNC + audio                  [current]
ag-04/    KasmVNC test                                             [explored]
ag-05/    Apache Guacamole test                                    [tested]
```

## Options for browser access to HEADLESS-1

All solutions below connect to the same virtual display (HEADLESS-1, port 5900 via wayvnc).

### Comparison

| Solution | Audio | Latency | Setup | UI | Interactive | Notes |
|----------|-------|---------|-------|----|-------------|-------|
| **noVNC (custom)** ag-03 | ffmpeg endpoint | Low | Easy | Basic | Yes | Working now |
| **noVNC (snap)** ag-03 | Same | Low | Easy | Default | Yes | Default UI |
| **KasmVNC** ag-04 | Built-in | Low | Medium (Docker/.deb) | Polished | Yes | Complex proxy setup |
| **Apache Guacamole** ag-05 | Built-in | Medium | Easy (oznu/guacamole Docker) | Rich | Yes | SQL injection needed for connections |
| **WebRTC (custom)** | Opus in WebRTC | Very low | Hard (signaling+encoding) | Custom | Limited (view-only or needs DataChannel) | Best for media |
| **MJPEG stream** (ag-03) | Separate | Medium | Easy | `<img>` | No | View-only |
| **HLS/DASH** | In container | High | Easy (ffmpeg) | `<video>` | No | View-only |

### Technology notes

**WebSocket vs WebRTC:**
- WebSocket = bidirectional TCP tunnel. noVNC sends raw pixel changes → browser renders via JS canvas (CPU). Audio needs separate HTTP stream. Good for interactive use (keyboard/mouse).
- WebRTC = peer-to-peer with negotiated codecs. H.264 video decoded in GPU. Opus audio. Very efficient for media. Needs signaling server for connection setup. Keyboard/mouse require a separate DataChannel.

**VNC protocol:**
- RFB is the raw VNC protocol: sends pixel data server→client, keyboard/mouse events client→server
- WebSocket wraps RFB so browsers can use it (TCP not available in JS)
- wayvnc --websocket serves both RFB and WebSocket on the same port

**Audio integration:**
- All VNC solutions need audio as a separate stream (VNC protocol has no audio)
- WebRTC is the only protocol that natively bundles video + audio in one stream
- Our current noVNC + ffmpeg endpoint works but can have sync issues

### Experiments completed

| # | Solution | Result |
|---|----------|--------|
| ag-03 | noVNC custom | Working: touchpad, keyboard, recording, TTS |
| ag-04 | KasmVNC | Explored: Docker runs own X11, not a proxy to wayvnc |
| ag-05 | Apache Guacamole | Working: oznu/guacamole connects via RFB to wayvnc:5900 |

### Next experiments

| # | Solution | Effort | Expected benefit |
|---|----------|--------|-----------------|
| ag-06 | WebRTC with wlroots capture | High | Hardware-accelerated video + audio, low latency |
| ag-07 | MJPEG/HLS fallback | Low | Quick test, view-only reliability |
