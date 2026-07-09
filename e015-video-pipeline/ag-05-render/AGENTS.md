# ag-05 — Render Video

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, GPU encoding, VAAPI
- [../AGENTS.md](../AGENTS.md) — pipeline flow, models, render parameters

## Model
`zai-coding-plan/glm-5v-turbo` (vision for review)

## Goal

Read transcriptions and render videos with various VFX, SFX, subtitles, and formats.

## Input

- `../ag-04/output/transcribe-manifest.csv` — transcriptions to render
- `../ag-04/output/script-NNN/*.srt` — subtitle files
- `../ag-04/output/script-NNN/*.txt` — text content

## Output

- `output/script-001/edge-jenny-v1.mp4` — video with VFX set 1
- `output/script-001/edge-jenny-v2.mp4` — video with VFX set 2
- `output/render-manifest.csv` — index of all rendered videos

### Render manifest (render-manifest.csv)
```csv
video_id,transcription_id,vfx,sfx,subtitle_config,format,file_path
001-v1,001-001,zoom+fade,none,size:32;color:white;animation:fade,vertical,script-001/edge-jenny-v1.mp4
```

## Render Parameters

Each video can vary:
- **VFX**: particles, glitch, zoom, pan, fade, color_grade, none
- **SFX**: typing, notification, ambient, none
- **Subtitles**: size (24-72), color, highlight_color, animation (fade/slide/pop), font
- **Scenes**: intro_duration, content_style, outro_duration
- **Format**: vertical (9:16, 608x1080) or horizontal (16:9, 1920x1080)

## Process

1. Read `../ag-04/output/transcribe-manifest.csv`
2. For each transcription, render multiple video variants:
   - Different VFX combinations
   - Different subtitle styles
   - Different formats (vertical/horizontal)
3. Use ffmpeg with VAAPI for encoding
4. Save videos to `output/script-NNN/`
5. Write manifest to `output/render-manifest.csv`

## FFmpeg Commands

### Vertical video (9:16) with subtitles
```bash
ffmpeg -f lavfi -i color=c=black:s=608x1080:d=120 \
  -vf "subtitles=subtitles.srt:force_style='FontSize=24,PrimaryColour=&Hffffff'" \
  -c:v h264_vaapi -vaapi_device /dev/dri/renderD128 \
  -vf "format=nv12,hwupload" \
  output.mp4
```

### Horizontal video (16:9) with subtitles
```bash
ffmpeg -f lavfi -i color=c=black:s=1920x1080:d=120 \
  -vf "subtitles=subtitles.srt:force_style='FontSize=48,PrimaryColour=&Hffffff'" \
  -c:v h264_vaapi -vaapi_device /dev/dri/renderD128 \
  -vf "format=nv12,hwupload" \
  output.mp4
```

## Self-command

```bash
tmux send-keys -t 15-5 "echo running ag-05" Enter
```

## Verification

1. Video files exist and are non-empty
2. Videos are playable (`ffprobe output.mp4`)
3. Subtitles are burned in and readable
4. Resolution matches format (608x1080 or 1920x1080)
5. Manifest CSV is valid
