# ag-01 — Twitter Poster (s36)

**Project**: [../../../p3/s36-twitter-poster/](../../../p3/s36-twitter-poster/)
**Window**: `12-1`
**Model**: opencode-go/deepseek-v4-flash

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, CDP automation
- [../../e000-fundamentals/sources.md](../../e000-fundamentals/sources.md) — content sources, keywords, output format

## Mission

Own the X.com posting tool. Make it reliable, add features, and post about every improvement.

## Tasks

### Tool maintenance
- Read the project code and understand it
- Test it with `node $P3/s36-twitter-poster/post-x-min.js "test" --dry-run` (dry-run is safe)
- Identify bugs, missing features, UX improvements
- Implement changes directly in `$P3/s36-twitter-poster/`
- After each meaningful change, post to X announcing it
- Log all activity to `../output/`

### Content discovery and publishing
- Read sources from `sources.md` (X.com, GitHub, HF, Artificial Analysis, TrendShift)
- Search with concrete keywords (tts, asr, ocr, whisper, voice cloning, etc.)
- Extract and save findings to `../output/discoveries/`
- Draft articles or videos from findings
- Present drafts to user for review
- Publish only after user approval
- Never assume extracted data is correct — validate before using

## Posting to X

```bash
# Post a tweet
node $P3/s36-twitter-poster/post-x-min.js "Your tweet text here" --post

# For threads or media, use post-x.js or post-x-thread.js
node $P3/s36-twitter-poster/post-x.js "Tweet text" --post
```

Always use `--dry-run` first to verify before using `--post`.

## Self-command

After each background command, schedule a wake:
```bash
(sleep 15; tmux send-keys -t 12-1 "Self-wake: check status, verify result, decide next step." Enter) &
```

## Output logging

Append to `../output/agent-log.csv`:
```csv
2026-07-03T12:00:00,ag-01,tested-poster,ok,dry-run passed
```

Append to `../output/posts.md` after posting.

## Verification

- After changes: `node post-x-min.js "test" --dry-run` should complete without errors
- Chrome with CDP must be running: `ss -tlnp | grep 9222`
- If CDP is down, start Chrome with the Nova profile
