# Video Review — ag-04 output

**File**: `../ag-04/video.mp4` (19 MB, 25fps, h264+aac)

---

## Checklist

### 1. Format — 9:16 vertical?

**FAIL.** The video is **1920x1080 (16:9 landscape)**, not 9:16 vertical. This is the opposite of what the AGENTS.md spec requires for mobile format. The entire video is horizontal.

### 2. Audio — real conversation (A↔B alternating)?

**PASS (partial).** The subtitles show a genuine back-and-forth dialogue between two personas in Spanish. The conversation flows naturally — questions, answers, examples, and closing. However, the audio is **mono (1 channel, 24kHz)**. For a two-person podcast, stereo separation or at least a higher sample rate would improve quality. I cannot verify speaker alternation from audio alone since I only have frames, but the subtitle text clearly shows alternating speakers.

### 3. Avatars — both personas visible? Good quality?

**PASS.** Both avatars are visible throughout the entire video side-by-side:
- **Left**: Male character — blue shirt, glasses, headphones, stubble
- **Left**: Female character — red shirt, braids, gold earrings, headphones

The avatars are clean cartoon/vector-style illustrations. They are static images (no lip-sync or animation) — both remain on screen simultaneously for the entire duration. This is acceptable for a simple podcast format but could be improved with subtle animations or speaker highlighting.

### 4. Subtitles — present and readable?

**PASS.** Subtitles are present in every frame, rendered in large white text with a dark outline. Font is clean and highly readable. The Spanish text is well-paced and matches the dialogue flow. Examples observed:
- `¿Has oído hablar de p4?`
- `No, no, nada que ver. p4 es un sistema donde los agentes de IA se comunican entre sí...`
- `¡Exacto! Uno sabe investigar, otro sabe escribir, otro sabe traducir.`
- `github.com/g8d3/p4. Ahí encuentras todo para empezar.`
- `¡Chao!`

No subtitle clipping or overlap issues detected.

### 5. Black frames — any?

**PASS.** ffmpeg blackdetect found zero black frames. All 10 sampled frames show the avatar layout with content.

### 6. Duration — reasonable?

**PASS.** Duration is **4:32 (272 seconds)**. Reasonable for a podcast explaining a concept — not too short, not too long.

---

## Summary

| Check | Result |
|---|---|
| Format 9:16 | FAIL — 16:9 landscape |
| Audio conversation | PASS — alternating dialogue, mono |
| Avatars visible | PASS — both present, static, good quality |
| Subtitles | PASS — clear, readable, well-paced |
| Black frames | PASS — none |
| Duration | PASS — 4:32 |

### Critical Issues

1. **Wrong aspect ratio**: 1920x1080 (16:9) instead of 9:16 (1080x1920). This is the most significant problem — the video will display sideways or letterboxed on mobile/vertical platforms (TikTok, Reels, Shorts).
