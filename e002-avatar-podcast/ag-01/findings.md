# Avatar Tool Research Findings

## Available Tools

### ffmpeg (6.1.1) — ✅ Recommended
- **Status**: Installed with extensive filter support
- **Capabilities**:
  - Composite static images with audio via `overlay`, `zoompan`, `fade`, `chromakey`
  - Draw text with `drawtext` filter
  - Encode H.264 at ~30-40x realtime speed
  - Full scriptable pipeline, no display needed
- **Limitations**: No 3D rendering, no lip-sync avatars natively
- **Test result**: Successfully composited colored circles with zoompan animation over background, muxed audio → MP4

### Chrome Headless (149.0.7827.53) — ✅ Available
- **Status**: Google Chrome installed, headless mode works
- **Capabilities**: Renders HTML+CSS+JS to screenshot PNG. Can animate with CSS/JS.
- **Limitations**: Captures only single frames (or via `--virtual-time-budget` for timing). To make video, need to capture frame sequence then encode with ffmpeg.
- **Test result**: Successfully rendered styled avatar HTML page to 640×480 PNG (39KB)

### OBS Studio (32.1.2) — ⚠️ Partial
- **Status**: Installed
- **Capabilities**: `--startrecording`, scene collections, virtual cam
- **Limitations**: **Not truly headless** — requires X display. Needs pre-configured scene collection (`.json`). Better for interactive / GUI use.
- **Test result**: CLI exists but needs GUI setup

## Unavailable Tools

| Tool | Status |
|------|--------|
| Godot 4 | ❌ Not installed |
| Kdenlive | ❌ Not installed |
| Blender | ❌ Not installed |

## Recommended Approach for ag-04

**Primary: ffmpeg-only pipeline**
- Use static PNG avatar images (two speakers side-by-side or picture-in-picture)
- Apply subtle animation via `zoompan` (gentle zoom), `fade` (in/out), and `overlay` (position avatars on background)
- Mux TTS audio from ag-03 as the audio track
- If subtitle text is needed, use `drawtext` filter

**If richer visuals are needed: Chrome + ffmpeg hybrid**
- Design avatar scene as HTML+CSS+JS with CSS animations
- Capture frames via Chrome headless → PNG sequence
- Encode to video with ffmpeg, mux audio

**Example command (ffmpeg-only approach):**
```bash
ffmpeg -loop 1 -i avatar1.png -loop 1 -i avatar2.png \
       -i background.png -i audio.mp3 \
       -filter_complex "\
         [2:v]scale=1920:1080[bg];\
         [0:v]scale=400:400,format=rgba,zoompan=z='zoom+0.002':d=150,setpts=PTS-STARTPTS[av1];\
         [1:v]scale=400:400,format=rgba,zoompan=z='zoom+0.002':d=150,setpts=PTS-STARTPTS[av2];\
         [bg][av1]overlay=x=100:y=200:shortest=1[bg1];\
         [bg1][av2]overlay=x=1420:y=200:shortest=1[vout]" \
       -map "[vout]" -map 3:a -c:v libx264 -preset medium -crf 23 \
       output.mp4
```
