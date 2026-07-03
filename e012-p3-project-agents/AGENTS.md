# e012 — P3 Project Agents

**Goal**: Many agents working in parallel, each owning a p3 project. Agents improve code, discover features, fix bugs, and post updates to X.com via CDP (using the Nova browser session).

## Inherits
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — AgentFS, tmux conventions, blocking commands, self-wake, CDP browser automation
- [../../p3/s36-twitter-poster/README.md](../../p3/s36-twitter-poster/README.md) — X posting via CDP

## Infrastructure

- **CDP browser**: Chrome running on `localhost:9222` with Nova's X.com session (see e000-fundamentals for startup)
- **Posting**: agents use `node $P3/s36-twitter-poster/post-x-min.js "text" --post` to tweet
- **p3 path**: `$HOME/code/p3` (available as env or by absolute path)

## Agents

| Window | Agent | Project | Provider | Mission |
|--------|-------|---------|----------|---------|
| `12-1` | ag-01 | s36-twitter-poster | opencode-go/deepseek-v4-flash | Own the poster: improve reliability, add features, post about updates |
| `12-2` | ag-02 | s44-content-agent | xiaomi-token-plan-sgp/mimo-v2.5 | Own the content pipeline: fix bugs, add sources, post about new features |
| `12-3` | ag-03 | s58-content-pipeline | zai-coding-plan/glm-4.7 | Own the video pipeline: improve quality, add platforms, post about releases |
| `12-4` | ag-04 | s33-evm-wallet-generator | opencode-go/mimo-v2.5 | Own the Zig wallet: optimize, add features, post about the tool |
| `12-5` | ag-05 | s17-terminal-ai-chat | xiaomi-token-plan-sgp/mimo-v2.5 | Own the terminal chat: fix UX, add providers, post about improvements |
| `12-6` | ag-06 | s10-contract-security | zai-coding-plan/glm-4.7 | Own the security app: audit, add endpoints, post about findings |

## Output

Agents log their activity to `output/`:

| File | Producer | Description |
|------|----------|-------------|
| `output/agent-log.csv` | All agents | timestamp,agent,action,status,details |
| `output/posts.md` | All agents | Log of every X post: date, agent, tweet text, link |
| `output/changes.csv` | All agents | Files modified, lines changed, feature summary |

Agents append to these files. No agent deletes or overwrites another agent's entries.

## Lifecycle

1. Launch agents in separate tmux windows (12-1 through 12-6)
2. Each agent reads its AGENTS.md, inherits e000-fundamentals, reads its project
3. Agent works: reads code, identifies improvements, implements them, verifies
4. Agent posts update to X via CDP
5. Agent logs to output/
6. Agent continues indefinitely (or until stopped)

## Coordination

- Agents work independently on different projects — no file conflicts
- Agents can post to X at any time via CDP
- The browser session is shared — agents should not close tabs used by others
