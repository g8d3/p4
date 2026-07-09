# Sources and output format

Preferred sources for content discovery and keywords for searching.

## Sources

| Source | What for | Access |
|--------|----------|--------|
| X.com bookmarks | Curated links saved by the user | ✅ AI can use |
| X.com search | Targeted discovery via keywords | ✅ AI can use |
| GitHub trending | Trending repos by language/category | ✅ AI can use |
| Hugging Face | Models, datasets, Spaces | ✅ AI can use |
| artificialanalysis.ai | Model benchmarks, cost-efficiency comparisons | ✅ AI can use |
| trendshift.io | Trending repos and dev tools | ✅ AI can use |
| X.com home feed | Trending topics, discussions | ❌ User only |

## Search keywords (X.com, GitHub, general)

Extracted from 100 user bookmarks (2026-07-09). Use these for content discovery.

### High frequency (use often)
- open source
- agent
- claude code
- coding agent
- voice cloning
- tts
- self hosted
- api
- github
- model

### Medium frequency
- cursor
- mcp
- skill
- linux
- terminal
- rust
- android
- voice arena
- realtime tts
- deepseek
- china
- free api

### Specific tools/projects
- codex
- anthropic
- openai
- cartesia sonic
- elevenlabs
- hermes agent

### General categories (for broad search)
- ai coding
- open source model
- voice ai
- chinese ai
- agent memory
- video generation
- screen recording
- browser automation

## Output formats

### Articles
- Short-form: tweet threads on X.com
- Description of what was found, with scepticism: "this repo claims X, my test showed Y"
- Link to source, disclaimer about verification level

### Videos
- Narration must match what is actually on screen — verified frame by frame
- Not acceptable: agent plans everything, records narration separately, then splices without checking
- Process: record interaction live → verify output matches narration → publish
- Exploratory format only (reactive, real-time), never scripted

## Workflow

1. Discover content from sources above using given keywords
2. Draft output (article/video)
3. Present to user for review
4. User approves or requests changes
5. Publish only after approval
