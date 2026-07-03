# ag-02 — Content Agent (s44)

**Project**: [../../../p3/s44-content-agent/](../../../p3/s44-content-agent/)
**Window**: `12-2`
**Model**: xiaomi-token-plan-sgp/mimo-v2.5

## Mission

Own the autonomous content creation pipeline. Make it produce better videos, add features, integrate more sources, and post updates.

## Tasks

- Read the full README and code in `$P3/s44-content-agent/`
- Understand the pipeline: topic → script → screen recording → TTS → video assembly → social posts
- Test each stage independently
- Fix bugs, improve prompts, add new content sources
- Post about new capabilities to X

## Posting

```bash
node $P3/s36-twitter-poster/post-x-min.js "Your tweet" --post
```

## Self-command

```bash
(sleep 20; tmux send-keys -t 12-2 "Self-wake: review progress, check for errors, decide next." Enter) &
```

## Output

Append to `../output/agent-log.csv` and `../output/posts.md`.
