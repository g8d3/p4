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

## Image sourcing for video visuals

Recurring question in every video build: **where do the images come from?**

The key clarification: **screen captures/recordings and generated images are
two INDEPENDENT dimensions, not two ranks of the same ladder.** They answer
different questions and are not interchangeable:

- **Reality dimension** — what actually happened: the tool, the terminal, the
  results, the session. When a video shows real work, *a capture is always
  preferable to a generated image of it* — more honest, free, instant.
- **Visual-support dimension** — everything that does NOT exist to capture:
  thematic scenes, characters, metaphors, backgrounds, illustration. This is
  what image generation is FOR.

Every element of a video picks one dimension based on what it must show, and
a priority order only exists *inside* each dimension.

### Reality dimension (real content) — priority order

| # | Source | When to use | How |
|---|--------|-------------|-----|
| 1 | **Live screen captures / recordings of the session** | The video shows real work: interactions, terminals, UIs, results, render progress | `grim`/`scrot` stills, `wf-recorder`/ffmpeg clips on the active display, `agent-browser screenshot`, `dapi screenshot`/`node capture` |
| 2 | **Existing p4 media / outputs** (from other experiments) | Real footage/frames/storyboards already produced in the p4 repo | Read `../<exp>/ag-<n>/output/`; `ffprobe` first (resolution/aspect vs the deliverable — p4 is mostly 608x1080 / 9:16) |
| 3 | **Stock / public-domain images** | Generic real-world filler: textures, photos, backgrounds | Wikimedia Commons, Openverse, Pexels/Unsplash (free license) |

### Visual-support dimension (generated content) — priority order

| # | Source | When to use | How |
|---|--------|-------------|-----|
| 1 | **AI-generated images (KIE Seedream)** | Thematic scenes, characters, storyboard grids, anything that doesn't exist to capture | `e019-kie-image-api/ag-01/bin/kie-image.sh` (text-to-image, or image-to-image with `--image-url` for character consistency). ~6.5 credits / 2K (~$0.03), async ~40 s, download immediately (expires ~20 min). |
| 2 | **Editor-native generation (`generate.*`)** | Compositions where the image must be declarative / part of the mount (Diffusion Studio) | `generate.image` in the JSX; feeds `generate.video`. Needs hosted backend + auth + credits; offline fails (`Missing authorization token`). |
| 3 | **AI video frames** (kling/seedance/veo via KIE) | Motion footage when no real footage exists | KIE video jobs; frames via `ffmpeg -ss …` or `dapi media grab`. Expensive, slow; last resort. |

Decision flow per element:
1. Does this element show **real work/interaction**? → capture it live (reality #1).
2. Does **p4 already have** this footage/image? → reuse it (reality #2).
3. Is it **generic decoration**? → stock (reality #3).
4. Is it a **specific scene/character/theme that doesn't exist**? → generate (support #1).
5. Must it stay **declarative inside a composition**? → `generate.*` (support #2).
6. Do you need **moving footage nobody captured**? → AI video (support #3).

A video mixes both dimensions freely: the demo video shows real captures of
dapi running (reality) AND generated/synthesized backgrounds and badges
(visual support) — they are not in competition.

### Generation is the default when no documented source exists

If there is **no documentation / no known source** for a visual-support
element, do NOT stall — **generate**. Whatever image model is available right
now (KIE Seedream today) is the answer, and the default way to generate is **a
grid, not one image at a time**:

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
- **Never generate what p4 already has.** `e018/e019/e023` are full of verified media; probe before you generate.
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
