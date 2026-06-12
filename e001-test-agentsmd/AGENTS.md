# e001 — Test AGENTS.md

**Goal**: Test and validate the nested AGENTS.md system by creating a video that explains the concept.

## What it does

This experiment produced a video (9:16 vertical) explaining the file-based multi-agent system:
- Multi-agent system without database or message bus
- Agent communication via nested AGENTS.md and directory structure
- Comparison with traditional approaches

## Structure

```
e001-test-agentsmd/
├── AGENTS.md      ← this file
└── ag-01/
    ├── AGENTS.md      ← agent process
    ├── guion.md       ← narration script
    ├── subtitles.srt  ← TikTok-style captions
    └── video.mp4      ← final output
```

## Lessons learned

- Steps are sequential (script → demo → recording → subtitles), not parallelizable with multiple agents.
- `edge-tts` with Colombian voice is far better than espeak-ng.
- Terminal font must be large (~22pt) to be readable in 9:16.
- Subtitles work best in short chunks with alternating colors (TikTok style).
- Use `ffmpeg -f x11grab -video_size 608x1080 -i :0.0+656,0` for 9:16 capture.
- Disable screen lock before recording (xset + xscreensaver).
- Verify the video is not black, has audio, and narration is synchronized.
