# Avatar System Quick Reference

## Controls (On-Screen)
- **1-finger drag** → rotate camera
- **Pinch** → zoom in/out  
- **Double-tap** → reset view

## Server Commands (WebSocket/HTTP POST)
```bash
# Load model
curl -X POST http://127.0.0.1:8787/cmd \
  -H 'Content-Type: application/json' \
  -d '{"cmd":"load","model":"model-a.vrm"}'

# Set expression
curl -X POST http://127.0.0.1:8787/cmd \
  -d '{"cmd":"expression","name":"happy","weight":1}'

# Speak with lip-sync
curl -X POST http://127.0.0.1:8787/cmd \
  -d '{"cmd":"speak","audio":"output/narration.mp3","mouth":"output/mouth.json"}'

# Get model info
curl -X POST http://127.0.0.1:8787/cmd \
  -d '{"cmd":"inspect"}'
```

## Tech Stack Summary
- **Render**: three.js + @pixiv/three-vrm + WebGL2
- **Server**: Node.js + ws (WebSocket)
- **TTS**: Deepgram Aura-2
- **Capture**: sway + wf-recorder
- **Encode**: VAAPI GPU H.264

## File Locations
- Server: `ag-01-avatar-core/server.js` (port 8787)
- Models: `models/model-a.vrm`, `models/model-b.vrm`
- Video assets: `ag-03-video/output/`

## Common Issues
- **Loading stuck**: Check server running, CORS headers
- **Commands timeout**: Client not registered, check WebSocket
- **Black screen**: Display access, verify sway running

## Full Documentation
See `TECH.md` for complete specs, protocol, pipeline details.