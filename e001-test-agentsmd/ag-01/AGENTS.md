# ag-01 — Subtitle fixer

## Goal

Fix the subtitle splitting in the existing video. Current subtitles sometimes break mid-phrase (e.g., "una base de datos ni un bus / de mensajes ni un orquestador").

## Task

Rewrite `subtitles.srt` so each entry splits at **natural phrase boundaries** (commas, periods, conjunctions) instead of fixed word counts.

### Rules

- Keep the same color cycling pattern (5 colors).
- Keep the same timing (match audio section durations).
- Each subtitle must be a complete thought fragment.
- Verify by reading through the SRT — no orphaned clauses.

### Steps

1. Fix `subtitles.srt` — rewrite with natural phrase boundaries.
2. Re-render `video.mp4` with the new SRT:
   ```
   ffmpeg -i /tmp/screen2.mkv -i /tmp/full_audio_edge.mp3 -vf "subtitles=subtitles.srt:force_style='FontName=Monospace,FontSize=17,MarginV=50,Alignment=2'" -c:v libx264 -preset ultrafast -c:a aac -shortest video.mp4 -y
   ```
3. Verify: the video file timestamp should be newer than the SRT file.

### Files

- `subtitles.srt` — rewrite this file
- `script.md` — reference for the text
- `video.mp4` — re-render after fixing SRT
