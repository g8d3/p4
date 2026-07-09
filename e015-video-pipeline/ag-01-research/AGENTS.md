# ag-01 — Research Topics

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, browser tools
- [../AGENTS.md](../AGENTS.md) — pipeline flow, models, TTS

## Model
`opencode-go/deepseek-v4-flash` (fast reasoning for search)

## Goal

Research topics from `topic_prompt.txt` and produce `output/topics.csv` with multiple video-worthy topics.

## Input

`topic_prompt.txt` — file with user's topic idea or keywords.

## Sources to Consult

| Source | What for | Access |
|--------|----------|--------|
| X.com bookmarks | Curated links saved by the user | ✅ AI can use |
| X.com search | Targeted discovery via keywords | ✅ AI can use |
| GitHub trending | Trending repos by language/category | ✅ AI can use |
| Hugging Face | Models, datasets, Spaces | ✅ AI can use |
| artificialanalysis.ai | Model benchmarks, cost-efficiency comparisons | ✅ AI can use |
| trendshift.io | Trending repos and dev tools | ✅ AI can use |
| X.com home feed | Trending topics, discussions | ❌ User only |

## Search Keywords

Extracted from 100 user bookmarks (2026-07-09).

### High frequency (use often)
- open source, agent, claude code, coding agent
- voice cloning, tts, self hosted, api
- github, model, cursor, mcp

### Medium frequency
- skill, linux, terminal, rust, android
- voice arena, realtime tts, deepseek, china
- free api, codex, anthropic, openai

### General categories
- ai coding, open source model, voice ai
- chinese ai, agent memory, video generation
- screen recording, browser automation

## Output

`output/topics.csv` — CSV with columns:
```csv
topic_id,title,category,summary,sources,potential_scripts
```

## Process

1. Read `topic_prompt.txt`
2. Use `agent-browser` to research the topic
3. Extract key insights, trends, angles
4. Write `output/topics.csv` with 3-5 video-worthy topics
5. Each topic should have: title, category (tech/education/news), summary, source URLs, potential script angles

## Tools

```bash
# Connect to Chrome (CDP running on port 9231)
agent-browser --auto-connect open "https://google.com"
agent-browser --auto-connect snapshot -i -c
agent-browser --auto-connect fill @e1 "search query"
agent-browser --auto-connect press Enter
agent-browser --auto-connect wait --text "results"
```

## Self-command

```bash
tmux send-keys -t 15-1 "echo running ag-01" Enter
```

## Verification

1. `output/topics.csv` exists and is valid CSV
2. At least 3 topics with non-empty titles and summaries
3. Sources are real URLs
