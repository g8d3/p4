# e044 — URL Video Queue

Web app: paste a URL (page, share link, video link) → it detects the videos on the
page → downloads them sequentially → merges them into one MP4 with ffmpeg.

Features:

- **Multi-tier detection**: plain HTML scan (video/source/meta/JSON-LD), yt-dlp
  (YouTube, playlists, 1000+ sites), headless Chrome via CDP for JS-only pages
  (Gemini share links, SPAs).
- **Queue**: many URLs, processed FIFO, one job at a time
  (`max_concurrent_jobs`). Sequential downloads inside a job.
- **Resource control**: `resource.cpu_percent` (ffmpeg threads), `resource.nice`,
  `resource.download_speed_limit_kbps` (0 = unlimited).
- **Time windows**: `time_windows` limits processing to parts of the day
  (cross-midnight supported, e.g. 21:00–10:00). Jobs go to `waiting_window`
  outside the window and resume when it opens.
- **Merge**: `-c copy` (no re-encode, ~0 CPU, works when segments share codec
  params — verified with Gemini videos) with automatic fallback to VAAPI
  re-encode when params differ.
- **Embeddable**: `create_app()` returns a FastAPI app mountable at any route:

```python
from fastapi import FastAPI
from app.main import create_app   # point PYTHONPATH at this experiment
parent = FastAPI()
parent.mount("/videos", create_app())
```

## Run

```bash
./bin/run.sh                          # venv + uvicorn on 127.0.0.1:8177
./bin/cli.sh submit https://share.gemini.google/eW3k7hp2itqF
./bin/cli.sh status                   # poll until done
./bin/cli.sh get <job_id>             # downloads merged-<job_id>.mp4
```

UI at http://127.0.0.1:8177 (mobile-friendly). Server is localhost-only; add
`allow_origins` + a reverse proxy if exposing it.

## Known working references

- `https://share.gemini.google/eW3k7hp2itqF` — Gemini share with 3 videos
  (`=mm,22,18,15` signed googlevideo URLs; direct download with redirect
  follow, no referer needed). Detection needs the browser tier.
- Direct `lh3.googleusercontent.com/gg/...` links without the mm suffix are
  JPEG posters, not videos — always download the full `src` (mm suffix).

## Architecture

```
app/main.py     FastAPI factory + API (jobs, detect, config) + lifespan worker
app/worker.py   queue consumer: detect → download each item → merge
app/detector.py detection chain: html → yt-dlp → CDP browser
app/cdp.py      minimal headless-Chrome CDP client (one shared Chrome)
app/merger.py   ffmpeg concat -c copy, fallback per-segment VAAPI re-encode
app/db.py       SQLite job store (WAL)
app/static/     single-page UI (vanilla JS, auto-refresh)
config.json     limits, windows, detection toggles
data/           runtime: queue.db, downloads/, output/, browser profile
```

## API

| Method | Path | Description |
|---|---|---|
| POST | `/api/jobs` | `{url}` or `{urls:[...]}` → 202 |
| GET | `/api/jobs` | list (newest first) |
| GET | `/api/jobs/{id}` | detail + items + progress |
| DELETE | `/api/jobs/{id}` | cancel (running) or remove (finished) |
| GET | `/api/jobs/{id}/video` | merged MP4 |
| POST | `/api/detect` | dry-run detection, no enqueue |
| GET/PUT | `/api/config` | runtime limits edit (persisted) |

## Inherits

- [../AGENTS.md](../AGENTS.md) — AGENTS.md to see the experiments list / conventions
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — command rules, hardware awareness
