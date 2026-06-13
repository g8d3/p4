# ag-04 — Video composer

## Goal

Compose the final avatar podcast video (9:16 vertical) with properly interleaved dialogue.

## Inputs

- `../ag-01/findings.md` — rendering approach
- `../ag-02/script.md` — dialogue with speaker sequence (A↔B alternating)
- `../ag-03/persona_a.mp3` — TTS for A (GonzaloNeural, male, 202s)
- `../ag-03/persona_b.mp3` — TTS for B (SalomeNeural, female, 66s)
- `../ag-03/timing.md` — duration notes

## Requirements (fixes from v1 + ag-05 review)

### 1. Format ✅ already working
- **9:16 vertical** (608x1080)
- H.264 video, AAC audio

### 2. Audio interleaving — FAILED in v1
The script has alternating A↔B↔A↔B dialogue. Your v1 played ALL of persona A (202s) then ALL of B (66s) — that's not a conversation.

**Fix**: 
- Read `../ag-02/script.md` lines in order. Each line is spoken by either A or B.
- Split each persona's MP3 into segment files matching each dialogue line.
- Concatenate segments in script order: `A1 + B1 + A2 + B2 + A3 + ...`
- Use ffmpeg concat demuxer:
  ```
  file 'seg_A1.mp3'
  file 'seg_B1.mp3'
  file 'seg_A2.mp3'
  ...
  ```
- Both personas should have roughly balanced speaking time (~50/50).

### 3. Avatars — FAILED in v1
Both avatars must be visible **at all times**, side by side (split-screen or PiP). When one speaks, they should be highlighted. Persona B appeared only for 5 seconds in v1.

Install Godot 4:
```
snap install godot-4
```
Create a scene with two avatar figures side by side, each with a name label. Add a speaking indicator (glow/highlight) that switches based on who is speaking.

If Godot is too complex, use Chrome headless with HTML+CSS+JS:
- Two avatar images side by side
- CSS animation to highlight the active speaker
- Capture frames with Chrome headless, compose with ffmpeg

### 4. Subtitles ✅ already present
Keep TikTok-style: short chunks, alternating colors, bottom position.

### 5. Render pipeline
Compose in order:
1. Generate Godot/HTML scene frames
2. Interleave audio segments per script order
3. Add subtitles
4. Encode to 608x1080 MP4

## Output

- `video.mp4` — final 9:16 video with balanced A↔B conversation

## Dependencies

ag-05 (reviewer) will check your output using Mimo vision.
