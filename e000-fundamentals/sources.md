# Sources and output format

Preferred sources for content discovery and keywords for searching.

## Sources

| Source | What for |
|--------|----------|
| X.com home feed | Trending topics, discussions |
| X.com bookmarks | Curated links saved by the user |
| X.com search | Targeted discovery via keywords |
| GitHub trending | Trending repos by language/category |
| Hugging Face | Models, datasets, Spaces |
| artificialanalysis.ai | Model benchmarks, cost-efficiency comparisons |
| trendshift.io | Trending repos and dev tools |

## Search keywords (X.com, GitHub, general)

Concrete terms, not semantic intent. Search engines don't do semantic search.

- tts
- asr
- ocr
- whisper
- voice cloning
- open source tts
- speech recognition
- cost per token
- latency benchmark
- model benchmark
- stt (speech to text)
- edge tts
- realtime tts
- video generation
- screen recording
- browser automation
- web scraper
- api wrapper
- cost-efficient (test if it works, may not)

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
