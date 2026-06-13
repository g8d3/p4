# ag-04 — Video composer

## Goal

Compose the final avatar podcast video using outputs from ag-01, ag-02, and ag-03.

## Inputs

- `../ag-01/findings.md` — recommended rendering approach
- `../ag-02/script.md` — dialogue script
- `../ag-03/persona_a.mp3` — TTS for persona A
- `../ag-03/persona_b.mp3` — TTS for persona B
- `../ag-03/timing.md` — duration info

## Task

Generate the final video. Start by reading ag-01's findings, then:

1. **Create avatar images** — two simple PNG avatars (can use `convert` from ImageMagick or draw with ffmpeg). Make them look like two different podcast hosts.
2. **Create background** — a podcast-style background image
3. **Compose** using the ffmpeg pipeline recommended by ag-01. The avatars should alternate speaking based on the script.
4. **Add podcast intro/outro** — brief title card at start, credits at end.

### Format

- 1920x1080 (16:9 landscape) — standard podcast format
- H.264 video, AAC audio
- Subtitles optional but nice to have

### Rules

- Follow ag-01's recommended approach unless it doesn't work.
- If the ffmpeg approach produces poor results, try the Chrome headless approach.
- Subtitles: TikTok-style but for landscape format (wider chunks, bottom-center).
- Verify output: check that audio plays, video is not black, both personas are visible.

### Files

- `video.mp4` — final output

### Dependencies

Wait for ag-03 to complete before starting.
