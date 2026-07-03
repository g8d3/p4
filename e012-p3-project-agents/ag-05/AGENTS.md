# ag-05 — Terminal AI Chat (s17)

**Project**: [../../../p3/s17-terminal-ai-chat/](../../../p3/s17-terminal-ai-chat/)
**Window**: `12-5`
**Model**: xiaomi-token-plan-sgp/mimo-v2.5

## Mission

Own the terminal AI chat app. Fix issues, add providers, improve TUI, and post about it.

## Tasks

- Read `$P3/s17-terminal-ai-chat/README.md` and all Python code
- Test that it runs: `cd $P3/s17-terminal-ai-chat && python main.py --help`
- Check SQLite schema, provider integrations, TUI rendering
- Fix bugs, add missing providers, improve UX
- Post about the chat app on X

## Posting

```bash
node $P3/s36-twitter-poster/post-x-min.js "Your tweet" --post
```

## Self-command

```bash
(sleep 20; tmux send-keys -t 12-5 "Self-wake: check status, continue working." Enter) &
```

## Output

Append to `../output/agent-log.csv` and `../output/posts.md`.
