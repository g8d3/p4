# VRM Avatar System Documentation

## Tech Stack

### Rendering & Avatar System
- **three.js** (v0.185.1): 3D graphics library for WebGL rendering
- **@pixiv/three-vrm** (v3.5.5): VRM file loading and runtime management
- **@pixiv/three-vrm-animation** (v3.5.5): VRMA animation support
- **WebGL2**: Hardware-accelerated rendering

### Server & Control
- **Node.js**: Backend server for avatar control
- **ws** (v8.21.3): WebSocket server for real-time commands
- **HTTP**: File serving (VRM models, audio, timeline files)

### Video Production Pipeline
- **Deepgram Aura-2**: Text-to-speech for narration
- **ffmpeg**: Audio processing and video encoding
- **sway**: Headless Wayland compositor for screen capture
- **wf-recorder**: Screen recording with hardware encoding
- **VAAPI**: GPU-accelerated H.264 encoding

## Control Protocol (JSON over WebSocket)

### Command Format
```json
{
  "cmd": "command_name",
  "client": "clientA|client-B|all",
  "param1": "value1",
  "param2": "value2"
}
```

### Available Commands

| Command | Parameters | Effect |
|---------|-----------|--------|
| `load` | `model`: "filename.vrm" | Load a VRM model |
| `expression` | `name`: "happy", `weight`: 0-1 | Set expression weight |
| `resetExpression` | `{}` | Clear all expressions |
| `lookAt` | `x`: -1 to 1, `y`: -1 to 1 | Set look-at target |
| `bone` | `name`: "leftUpperArm", `rotate`: [x,y,z] | Direct bone control |
| `animation` | `url`: "file.vrma", `loop`: true | Play VRMA animation |
| `speak` | `audio`: "narration.mp3", `mouth`: "mouth.json" | Play audio + lip-sync |
| `setIdle` | `on`: true/false | Enable/disable idle animations |
| `inspect` | `{}` | Get model state and info |

### Response Format
```json
{
  "ok": true,
  "cmdId": "timestamp-random",
  "clientId": "clientA",
  "result": { ... }
}
```

## File Structure

```
e030-vrm-avatar/
├── models/              # VRM model files
│   ├── model-a.vrm     # Character A (sample)
│   └── model-b.vrm     # Character B (Seed-san)
├── ag-01-avatar-core/  # Server + client-A
│   ├── server.js       # HTTP+WS server on 8787
│   ├── viewer.html     # Three.js client-A
│   └── package.json    # Dependencies
├── ag-02-client-b/     # Client-B (alternate implementation)
│   └── viewer-B.html   # Second three.js client
├── ag-03-video/        # Video production
│   ├── output/
│   │   ├── narration.mp3       # TTS audio
│   │   ├── mouth.json          # Lip-sync timeline
│   │   ├── performance.json    # Commands with timing
│   │   ├── transcript.json     # Word timestamps
│   │   ├── capture.mp4         # Raw screen recording
│   │   ├── final.mp4           # VAAPI-encoded final video
│   │   └── metadata.json       # Production metadata
│   └── narration.txt   # Script text
```

## Client Controls

### Mobile (Touch)
- **Single-finger drag**: Rotate camera around avatar
- **Pinch (two fingers)**: Zoom in/out
- **Double-tap**: Reset camera to default view

### Desktop (Mouse)
- **Mouse drag**: Rotate camera around avatar
- **Scroll wheel**: Zoom in/out

## Performance Script Format

```json
[
  {"time": 0, "command": "load", "payload": {"model": "model-a.vrm"}},
  {"time": 1000, "command": "expression", "payload": {"name": "happy", "weight": 1}},
  {"time": 2000, "command": "speak", "payload": {"audio": "narration.mp3", "mouth": "mouth.json"}},
  {"time": 7000, "command": "expression", "payload": {"name": "neutral", "weight": 1}}
]
```

## Mouth Timeline Format

Lip-sync data extracted from audio RMS energy:
```json
[
  [0, 0.0],     // [time_ms, mouth_weight_0_to_1]
  [100, 0.2],   // 100ms after start, 20% mouth open
  [200, 0.5],   // 200ms after start, 50% mouth open
  ...
]
```

## Video Pipeline

1. **TTS**: Generate narration audio (Deepgram Aura-2)
2. **Lip-sync**: Extract RMS energy from audio → mouth.json
3. **Performance**: Create timed command sequence
4. **Capture**: Run performance while recording screen
5. **Encode**: Convert to VAAPI GPU-encoded H.264
6. **Metadata**: Document all tools and settings

## VRM Models

- **Model A**: `VRM1_Constraint_Twist_Sample.vrm` (pixiv sample)
- **Model B**: `Seed-san.vrm` (VirtualCast character)

Both models support:
- Full humanoid bone hierarchy (50+ bones)
- 18 blendshape expressions (aa, ee, oh, happy, sad, angry, etc.)
- Spring bones for physics (hair, cloth)
- VRM 1.0 specification

## Caching

- **Three.js assets**: Browser cache via HTTP headers
- **VRM models**: Served with `Cache-Control: no-store` (prevent stale versions)
- **Audio/timelines**: Cached by browser

## Production Settings

- **Resolution**: 608×1080 (9:16 vertical)
- **Frame rate**: 60 FPS
- **Encoding**: H.264 VAAPI (hardware GPU)
- **Bitrate**: Auto-tuned for quality
- **Format**: MP4 container, AAC audio

## Troubleshooting

### Loading stuck at 0%
- Check browser console for CORS errors
- Verify server is running on port 8787
- Ensure models directory exists and contains .vrm files

### WebSocket connection failed
- Check server logs for "avatar-server listening"
- Verify WebSocket URL: `ws://127.0.0.1:8787/` (or external IP)
- Check firewall allows port 8787

### Commands timeout
- Ensure client is registered (`type: 'registered'` message)
- Check client console for errors
- Verify command format matches protocol spec

### Capture fails / black screen
- Verify sway is running headless
- Check wf-recorder has display access
- Test with static page first (no avatar)