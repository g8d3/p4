# e011 — GitHub Repo Analysis

**Goal**: Test and compare GitHub repos for AI video creation and AI social media automation (user data extraction, searching, posting). Produce comparative tables and recommendations.

## Inherits
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — principles, display/window management, CDP/agent-browser, browser automation

## Resources

- **X.com bookmarks** at `x.com/i/bookmarks` — large collection of repos to test
- **TikTok likes/collections** — interesting video content, potential repos
- **3 AI subscriptions**: Xiaomi, OpenCode Go, Z.AI (one per agent)

## Agents

| Window | Agent | Provider | Task |
|--------|-------|----------|------|
| `11-1` | ag-01 | Xiaomi | Extract x.com bookmarks → `output/bookmarks.txt` |
| `11-2` | ag-02 | OpenCode Go | Research AI video creation repos → `output/video-repos.md` |
| `11-3` | ag-03 | Z.AI | Research social media automation repos → `output/social-repos.md` |

## Output

Shared `output/` directory serves as the orchestration layer:
- `output/bookmarks.txt` — produced by ag-01, consumed by ag-02/ag-03
- `output/video-repos.md` — produced by ag-02
- `output/social-repos.md` — produced by ag-03

Agents read from and write to `output/`. The filesystem IS the orchestrator — no
message broker, no coordination code. Each agent is a pure function: read input,
produce output.

## Shared tools

- `ag-02/` contains `twitter_bookmark_scrapper.py` (Playwright) for bookmark extraction
- `ag-01/` contains Agent-Reach CLI (multi-platform search/read tool)
- Chrome with CDP on port 9222 (started by ag-01)

## Infrastructure

- Chrome with CDP runs on HEADLESS-1 (Wayland)
- agent-browser CLI for automated interaction
- Screen visible via VNC on port 5900

## Model selection

Each agent uses a different provider to maximize parallel throughput:
- ag-01: `xiaomi-token-plan-sgp/mimo-v2.5`
- ag-02: `opencode-go/deepseek-v4-flash`
- ag-03: `zai-coding-plan/glm-4.7`
