# ag-04 — Video composer

## Goal

Compose the final avatar podcast video (9:16 vertical) with properly interleaved dialogue.

## Inputs

- `../ag-01/findings.md` — rendering approach
- `../ag-02/script.md` — dialogue with speaker sequence (A↔B alternating)
- `../ag-03/persona_a.mp3` — TTS for A (GonzaloNeural, male, 202s)
- `../ag-03/persona_b.mp3` — TTS for B (SalomeNeural, female, 66s)
- `../ag-03/timing.md` — duration notes

## Requirements (fixes from v1)

### 1. Format
- **9:16 vertical** (608x1080), like e001 video
- H.264 video, AAC audio

### 2. Audio interleaving
Do NOT put persona_a.mp3 then persona_b.mp3 sequentially. Instead:
- Read `script.md` to get the exact A↔B↔A↔B sequence
- Cut each audio file into segments matching each dialogue line
- Interleave segments in the correct conversation order
- Use `ffmpeg` concat or frame-level editing

### 3. Avatars
Install Godot 4 if not available:
```
snap install godot-4
```
Create a simple scene with two avatar figures side by side. Alternative: use Chrome headless HTML+CSS for animated avatars.

### 4. Subtitles
TikTok-style: short chunks, alternating colors, bottom position.

### 5. Render pipeline
```
ffmpeg ... (complex filter for avatars + audio interleave + subtitles)
```

## Output

- `video.mp4` — final 9:16 video with interleaved podcast

## Dependencies

ag-05 (reviewer) will check your output using Mimo vision.
