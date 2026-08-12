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

## Image sourcing priorities (for video visuals)

Recurring question in every video build: **where do the images come from?**
Answer in priority order — never jump to a lower tier while a higher one
fits. The rule of thumb: *real content from the session first, real
p4/pipeline media second, generated assets only for what doesn't exist.*

| # | Source | When to use | How | Cost / risk |
|---|--------|-------------|-----|-------------|
| 1 | **Session captures** (screenshots of what actually happened) | Exploratory/reactive videos: the agent's own interactions, terminals, UIs, results | `grim`/`scrot` on the active display, `agent-browser screenshot`, `dapi screenshot`/`node capture` | Free, always truthful, zero latency. Preferred when the video shows real work. |
| 2 | **Existing p4 media / outputs** (from other experiments) | Any real footage, frames, storyboards already produced in the p4 repo | Read `../<exp>/ag-<n>/output/` for `.mp4`/`.png`; `ffprobe` first to check resolution/aspect | Free, offline, already verified by the producing agent. Check aspect ratio matches the deliverable (p4 is mostly 608x1080 / 9:16). |
| 3 | **Stock / public-domain images** | Generic filler, textures, backgrounds, icons when no session or p4 content applies | Wikimedia Commons, Openverse, Pexels/Unsplash (free license), e.g. `dapi fetch` for video | Free but needs attribution review; remote URLs need network at mount time. |
| 4 | **AI-generated images (KIE Seedream)** | Thematic moments, character design, storyboard grids, scenes that don't exist anywhere | `e019-kie-image-api/ag-01/bin/kie-image.sh` (text-to-image or image-to-image with `--image-url` for character consistency) | ~6.5 credits / 2K image (~$0.03); async ~40 s; results expire ~20 min, download immediately. |
| 5 | **Editor-native generation (`generate.*`)** | Compositions where the image must be declarative / part of the mount (Diffusion Studio) | `generate.image` in the JSX; feeds `generate.video` for motion | Hosted backend: needs account + auth token + credits. Offline it fails (`Missing authorization token`). |
| 6 | **AI video frames** (kling/seedance/veo via KIE) | Motion footage when no real footage exists | KIE video jobs; frames via `ffmpeg -ss …` or `dapi media grab` | Expensive, slow; last resort for footage. |

Decision flow:
1. Does the video show real work/interaction? → **tier 1** (capture it live).
2. Does another p4 experiment already have the footage/image? → **tier 2**.
3. Is it generic decoration? → **tier 3** (free stock).
4. Is it a specific scene/character that doesn't exist? → **tier 4** (KIE Seedream).
5. Is it part of a Diffusion Studio composition that must stay declarative? → **tier 5** (only if backend available).
6. Do you need moving footage nobody captured? → **tier 6** (AI video).

### Generation is the default when no documented source exists

If there is **no documentation / no known source** for the images a video
needs, do NOT stall looking for a source — **generate**. Whatever image model
is available right now (KIE Seedream today) is the answer, and the default way
to generate is **a grid, not one image at a time**:

1. **One KIE request asks for a grid** of related images (storyboard grid,
   character reference sheet, a scene pack) instead of N single-image
   requests. One call ≈ 1 image cost for N cells — ~16× cheaper and faster
   for a 4×4 storyboard. The storyboard template at
   `prompts/storyboard.md` already does this (16 cells, single request).
2. **A vision model decodes the grid** (mimo-v2.5 / kimi-k2.7 / glm-5.x):
   it returns the cell count, the layout (rows × columns), and a per-cell
   description. Validated 2026-08-12 on a p4 grid: *"6 cells, 3 rows × 2
   columns, character reference sheet, one line per expression."*
   Command: `opencode run -m opencode-go/mimo-v2.5 "read <grid.png>: how many
   cells, layout, one line per cell"`.
3. **Crop the grid** into individual cell images (programmatic crop by
   rows/columns — a 4×4 grid of 2576×1456 → 16 cells of ~644×364, or use the
   vision model's reported geometry).
4. Each cell is now a usable scene image; the vision model's per-cell
   descriptions tell you exactly which cell goes where in the storyboard.

So generation-as-default means: **grid in, vision decode, cells out** —
cheaper than single images, and the grid doubles as the storyboard artifact.

Hard rules:
- **Never generate what you can capture.** A screenshot of the real tool is more honest, free, and faster than an AI image of it.
- **Always reuse p4 output before generating.** `e018/e019/e023` are full of verified media; probe before you generate.
- **Generation is the tie-breaker, not the first resort** — but when no source applies, generate rather than stall; prefer the grid+vision+crop pattern over N single requests.
- **Aspect ratio consistency**: every image used in a video must match the deliverable's aspect ratio (p4 mobile = 9:16, this experiment's demo = 16:9). Crop/`objectFit` to fit, never mix ratios.
- **Storyboards**: generated via the single-request KIE grid (`prompts/storyboard.md`), but real screen captures replace grid cells when the video shows computer events.
- **Verify after every fetch**: `ffprobe` images/videos for dimensions; never trust a URL or a generator's promise — check the file. For grids, the vision model's decode must match what the crop produces — check a cell after cropping.

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
