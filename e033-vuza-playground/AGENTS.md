# e033 — VUZA Playground (free AI video creator + Pinterest scraper)

Playground for [**VUZA**](https://github.com/AliRash3ed/VUZA-Free-AI-Video-Creator-and-Pinterest-Video-Scraper)
(`AliRash3ed/VUZA-Free-AI-Video-Creator-and-Pinterest-Video-Scraper`) — a free,
open-source "faceless video" generator: script → AI keywords → stock media →
edge-tts voiceover → moviepy subtitled vertical video. Markets itself as a
**"world's first free Pinterest video scraper"** and a zero-cost alternative to
Pictory/InVideo/MoneyPrinter Turbo.

Scope of this experiment: **verify the marketing claims against reality**, get it
running, and find/trace what actually works.

## Verified findings (2026-08-18)

| Claim | Verdict | Evidence |
|---|---|---|
| Installs & runs | ✅ | venv + `pip install -r requirements.txt`, `python app.py` → FastAPI on `:8000` |
| Web UI + REST API | ✅ | `/api/status`, `/` both 200; all routes registered |
| "Bring your own AI" (OpenAI-compatible) | ✅ | wired to `opencode-go` (`deepseek-v4-flash`) — script gen + per-sentence keyword extraction work |
| Edge-TTS voiceover | ✅ | `edge-tts 7.2.8`, voiceover MP3s generated |
| Video assembly (moviepy 2.2) | ✅ after 1-line fix | 7.6s 9:16 captioned video, audio track present |
| **Pinterest scraper (headline feature)** | ❌ **blocked** | headless Chromium hits Pinterest sign-in modal → **0 pins** |

### The Pinterest wall (headline claim is false out-of-the-box)

`PinterestScraper.get_pin_urls` opens `pinterest.com/search/videos/?q=...` with
headless Playwright Chromium and looks for `a[href*="/pin/"]`. Pinterest serves
a **sign-in / "You are signed out" modal** to unauthenticated headless browsers;
the page body renders video durations (0:15, 0:10 …) but **no `/pin/` anchors** →
`get_pin_urls` returns 0 → `search_videos` returns [].

Details found while diagnosing:
- With the stock `wait_until="networkidle", timeout=60000` the page often comes
  back **empty** (title `Pinterest - Colombia`, 0 body chars). `wait_until='load'`
  (or `domcontentloaded`) yields real HTML (~1.1 MB) after a 302 geo-redirect to
  `co.pinterest.com` — but still shows the login modal.
- `a[href*="/pin/"]` count = 0 even when results are visually present; result
  links in the signed-out grid use a different structure.

**To actually scrape Pinterest you need a signed-in session** (e.g. drive the
real Chrome with the main `chrome-main` profile via CDP). Not implemented here;
documented as the next step.

### One-line bug fix (video_engine.py, photo branch)

`create_video()` re-imports `ImageClip` inside the watermark `if` block. That
makes `ImageClip` a function-local for the whole function, so the **photo** path
(`ImageClip(selected_photo)…`) raises `UnboundLocalError`. Fixed by removing the
redundant local import (module-level import at line 7 already provides it).
The **video** path is unaffected.

## Layout

| Path | What |
|---|---|
| `repo/` | Upstream VUZA source (cloned, `.git` stripped, small 272K — committed). `repo/video_engine.py` carries the one-line fix |
| `venv/` | Python 3.12 venv (gitignored) |
| `bin/test_pipeline.py` | Reproducible smoke test: placeholder media + edge-tts + moviepy assembly |
| `downloads/` | Scraper outputs (gitignored — binary media) |
| `output/` | Deliverables / test renders (gitignored) |

## Wiring the AI brain to our own provider

VUZA's `LLMProcessor` takes any OpenAI-compatible `chat/completions` endpoint.
We point it at opencode-go (no OpenRouter key needed):

```python
from aesthetic_scraper import LLMProcessor
base = os.environ["OPENCODE_GO_BASE_URL"].rstrip("/")
llm = LLMProcessor(
    api_key=os.environ["OPENCODE_GO_API_KEY"],
    api_url=base + "/chat/completions",
    model=os.environ["OPENCODE_GO_MODEL"],   # deepseek-v4-flash
)
```

`generate_full_script(topic, vibe)` → punchy one-sentence-per-line script; then
`extract_keywords(script, vibe)` → `[{sentence, keyword}]` for stock search.

## Reproducing the pipeline test

```bash
cd e033-vuza-playground
./venv/bin/python bin/test_pipeline.py
# → output/pipeline_test/final_aesthetic_video.mp4  (~7.6s, 9:16, edge-tts + subtitles)
```

It places two generated gradient images under `output/pipeline_test/project/<keyword>/`,
generates edge-tts voiceovers, and runs `VideoEngine.create_video`. **Media
sourcing is the only external dependency** — this proves script→voice→video with
no stock API.

## Caveats

- VUZA writes its final video with `codec='libx264'` (CPU). p4's final-video rule
  demands `h264_vaapi` — that's a VUZA-internal default; re-encode deliverables
  with `e000-fundamentals/.../encode_vaapi.sh` if kept.
- `write_videofile(threads=4)` — moderate CPU during render (fine in daytime).
- Pexels / Pixabay sources need API keys (none on this machine) → return `[]` when
  unset. Only Pinterest is key-free — and it is the one that is blocked.
- Playwright Chromium must be installed (`./venv/bin/playwright install chromium`).

## Next steps (ideas)

1. Pinterest with a signed-in session: launch real Chrome (`chrome-main` profile)
   via CDP, run the search there, extract pins, feed yt-dlp.
2. Point the LLM brain + video pipeline at a real stock source (get a Pexels key)
   to produce a true zero-touch faceless video.
3. Patch `write_videofile` to `h264_vaapi` for p4-grade GPU encodes.

## Session trail

Recorded 2026-08-18. See `e000-fundamentals/trail.md`.
