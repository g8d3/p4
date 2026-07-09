# ag-06 — Merge Audio + Video

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles
- [../AGENTS.md](../AGENTS.md) — pipeline flow, models

## Model
`cmd -m xiaomi/mimo-v2.5` (14× deal, cheap verification)

## Goal

Merge rendered videos with their corresponding audio files to produce final output.

## Input

- `../ag-05/output/render-manifest.csv` — rendered videos
- `../ag-03/output/audio-manifest.csv` — audio files
- `../ag-05/output/script-NNN/video-*.mp4` — video files
- `../ag-03/output/script-NNN/*.mp3` — audio files

## Output

- `output/script-001/edge-jenny-v1-FINAL.mp4` — final video with audio
- `output/merge-manifest.csv` — index of all final videos

### Merge manifest (merge-manifest.csv)
```csv
final_id,video_id,audio_id,file_path,file_size_mb
001-v1,001-v1,001-001,script-001/edge-jenny-v1-FINAL.mp4,15.2
```

## Process

1. Read `../ag-05/output/render-manifest.csv`
2. Read `../ag-03/output/audio-manifest.csv`
3. For each video, find matching audio:
   - Match by script_id (video from script-001 uses audio from script-001)
   - Match by voice (edge-jenny video uses edge-jenny audio)
4. Merge video + audio using ffmpeg
5. Save final videos to `output/script-NNN/`
6. Write manifest to `output/merge-manifest.csv`

## FFmpeg Commands

### Merge video + audio (copy video, encode audio)
```bash
ffmpeg -i video.mp4 -i audio.mp3 \
  -c:v copy -c:a aac -b:a 192k \
  output-FINAL.mp4
```

### Merge with audio replacement (re-encode both)
```bash
ffmpeg -i video.mp4 -i audio.mp3 \
  -c:v h264_vaapi -vaapi_device /dev/dri/renderD128 \
  -vf "format=nv12,hwupload" \
  -c:a aac -b:a 192k \
  output-FINAL.mp4
```

## Self-command

```bash
tmux send-keys -t 15-6 "echo running ag-06" Enter
```

## Verification

1. Final video files exist and are non-empty
2. Videos have both video and audio streams (`ffprobe`)
3. Audio matches video duration
4. File sizes are reasonable
5. Manifest CSV is valid
