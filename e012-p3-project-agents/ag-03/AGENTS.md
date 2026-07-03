# ag-03 — Content Pipeline (s58)

**Project**: [../../../p3/s58-content-pipeline/](../../../p3/s58-content-pipeline/)
**Window**: `12-3`
**Model**: zai-coding-plan/glm-4.7

## Mission

Own the weekly video pipeline. Make it robust, add platform support, improve video quality, and post about releases.

## Tasks

- Read `$P3/s58-content-pipeline/README.md` and all code
- Understand the flow: topic → opencode → TTS → long video → shorts → social platforms
- Test TTS, ffmpeg assembly, short splitting
- Add TikTok/IG posting if missing
- Post about working pipeline

## Posting

```bash
node $P3/s36-twitter-poster/post-x-min.js "Your tweet" --post
```

## Self-command

```bash
(sleep 20; tmux send-keys -t 12-3 "Self-wake: check progress, fix issues, keep going." Enter) &
```

## Output

Append to `../output/agent-log.csv` and `../output/posts.md`.
