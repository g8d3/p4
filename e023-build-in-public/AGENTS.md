# e023 — Build in Public: AI systems channel

**Goal**: A YouTube channel where each episode documents a real AI-system build from this repo (p4). The repo is the source material. The channel builds audience trust through demonstrated, verifiable work — not through generic AI tutorials.

**Channel identity** (working title): "I build AI systems in public. Here's the honest truth." Every episode = one real experiment, told reactively while it runs.

**Core rule**: the work product IS the content. No scripted filler, no generic "what is AI" explainers. Each episode comes from an actual experiment in this repo — what was tried, what failed, what was learned, with real screens, real commands, real numbers.

## Architecture: parallel full-stack producers

Each agent is a **full-stack producer** — it owns an episode end-to-end: picks the topic, runs the experiment live, narrates reactively, captures, assembles, and writes its own publish kit. No handoff between a "story" agent and a "production" agent, because the reactive narration only exists inside the agent's head during the run.

**Scaling = more producers in parallel.** Launch N producers simultaneously (on different providers to maximize throughput) and each produces a complete video start-to-finish.

```
ag-01 (trading/finance domain)  ──→ episode.mp4 + metadata.json + publish-kit.md
ag-02 (agent-systems domain)    ──→ episode.mp4 + metadata.json + publish-kit.md
ag-03 (browser/tech domain)     ──→ episode.mp4 + metadata.json + publish-kit.md
```

Each producer writes its deliverables to its own `output/`, then appends a row to its `output/episode-log.csv`.

## Producer domains

Producers are differentiated by **topic domain** so parallel runs don't collide and each builds a consistent series identity:

- **ag-01** — Trading & finance systems (e021 Hyperliquid playground, e022 Nautilus grid)
- **ag-02** — Agent & AI systems (e007 self-documentation, e011 repo analysis, e012 p3 agents, e008 assistant)
- **ag-03** — Browsers & undetectable tech (e018 HyperFrames, e020 undetectable-browser benchmark, e013 share extractor)

## Format

- **Primary**: YouTube long-form (16:9, 1920x1080), 5-15 minutes
- **Later phase**: cut 9:16 vertical shorts from each episode (only once long-form publishing is proven, ≥3 episodes)
- **Language**: English
- **Type**: exploratory/reactive only — the agent thinks and reacts live, never scripts and narrates over a recording

## Output per producer

- `output/episode-brief.md` — plan: hook, story arc, key moments, format (written by the producer itself, before running)
- `output/episode.mp4` — final long-form video
- `output/metadata.json` — resource metadata (per fundamentals)
- `output/narration.txt` — transcript
- `output/publish-kit.md` — title, description, chapters, tags, thumbnail prompt, upload checklist
- `output/episode-log.csv` — one row per episode (date, experiment, topic, duration, title)

## Sequence per episode (within each producer)

1. Pick an experiment from its domain, write the plan (hook, arc, key moments).
2. Run the experiment live with reactive narration; capture continuously.
3. TTS → transcribe → assemble the video.
4. Verify: not black, audio present, narration matches screen.
5. Write the publish kit + append to the episode log.

## Pitfalls

- Do not reuse old videos. Every episode must be a fresh, real run.
- The reactive rule is absolute: no pre-written narration over a recorded run.
- Verify the video: not black, audio present, narration matches screen.
- Episode topic and aspect ratio must be decided up front, before production starts.
- Keep honest failures in. The channel's value is the honest truth, not the success.
- Producers must pick **distinct** experiments within their domain on parallel runs; check `output/episode-log.csv` to avoid repeating a published episode.

## Parallel safety (decentralized arbitration)

Producers run simultaneously. The design principle: **no centralized arbiter — each resource coordinates itself, and each agent is smart enough to check before acting.** Do NOT build a lock system; the tools already arbitrate.

1. **Virtual displays**: each producer owns its OWN display. Never share. Claim yours by number:
   - ag-01 → `HEADLESS-1`, ag-02 → `HEADLESS-2`, ag-03 → `HEADLESS-3`
   - Create it if missing: `swaymsg --socket /tmp/opencode/sway-e023.sock create_output`
   - Verify it exists and is free before using: check `swaymsg -t get_outputs` / `pdw ls`
   - Record only YOUR display: `wf-recorder -o HEADLESS-N`
   - Displays are never a shared resource — each agent is the sole owner of its number.

2. **Transcription server** (`:9877`): the server is single-threaded and **queues automatically** — concurrent requests are served one at a time, each getting its answer when resources allow. Agents simply POST and wait. No coordination needed, no special handling. (Verified: `HTTPServer` serializes requests.)

3. **GPU/VAAPI encoder**: concurrent encodes share the GPU and time-slice. If the GPU is saturated, encodes just take longer — that is correct behavior, not a conflict. Do not try to serialize; just wait for your encode to finish.

4. **TTS (KIE API)**: rate limit is 20 req/10s, shared across all producers. If you get rate-limited, back off and retry — the API arbitrates. Do not fight it.

5. **Before acting on any shared resource, check current state first** (`pgrep`, `pdw ls`, health checks). If something looks busy, it is — wait or use your own instance. Never assume.

6. **Orphan cleanup (mandatory)**: an interrupted run can leave a wf-recorder running with no owner, eating CPU and holding a display. Rules:
   - BEFORE starting your capture: `pgrep -a wf-recorder` — if a recorder is running on a display that is NOT yours, leave it alone; if it is yours or appears orphaned (no agent actively using it), kill it by PID.
   - AFTER finishing capture: verify your recorder stopped (`pgrep -a wf-recorder`). If one lingers, kill it by PID.
   - Never `pkill wf-recorder` broadly — another producer may be recording its own display. Kill by exact PID only.

The orchestrator's only review job: confirm no producer is stuck (tokens frozen, no output growing), each is on its own display, and no orphaned recorders linger. Quality review of the video happens inside each producer.

## Resource monitoring & GPU enforcement

**Monitor** (run from the orchestrator or any agent, periodically):
```bash
bash e023-build-in-public/bin/monitor.sh
```
Reports: GPU busy %, top CPU consumers, wf-recorder/ffmpeg processes, **flags any CPU encoder in a final-assembly ffmpeg pipeline**, per-producer window status, transcribe+worker health. Exit 0 = clean, 1 = violation found.

**GPU rules (absolute):**
- The FINAL video encode MUST be `h264_vaapi` — via `e023-build-in-public/bin/encode_vaapi.sh <input> <output>`. CPU encoders (`libx264` etc.) for final videos are forbidden.
- The ONLY allowed libx264 is wf-recorder capture (fundamentals: VAAPI corrupts headless captures). Re-encode that capture with `encode_vaapi.sh` afterward.
- Verify every final video with: `ffprobe ... -show_entries stream_tags=encoder` → must contain `vaapi`. Both libx264 and vaapi report codec `h264`, so check the ENCODER tag, not the codec. (The encoder name is a stream *tag*, not a direct stream field — `stream=encoder` returns empty.)

**Signs of a CPU-encode problem**: machine gets loud/fans spin, GPU busy stays low while one process eats 150-200% CPU. When in doubt, run `monitor.sh`.

**Transcribe server (shared, single-threaded)**: if `/health` hangs or returns nothing, the server is stuck on a leaked connection (seen: CLOSE-WAIT pileup). Restart it (worker survives):
```bash
kill $(pgrep -f "python3 transcribe_server" | head -1)
cd e018-hyprframes-browser-video/ag-02 && nohup python3 bin/transcribe_server.py > /tmp/transcribe_server.log 2>&1 &
curl -s http://127.0.0.1:9877/health   # must return {"status":"ok"}
```
Do NOT restart the ASR worker (`model_worker.py`) — it takes ~20s to reload the model.

## Orchestration

- Launch with: `tmux new-window -n 23-N -d`, cd into the producer dir, `. ~/.zshrc && <launch>`, send "Read AGENTS.md, then read each file listed in Inherits. Execute the task."
- Launch commands by provider priority:
  - opencode-go: `opencode -m opencode-go/deepseek-v4-flash`
  - Command Code: `cmd -m deepseek/deepseek-v4-pro --trust --yolo --skip-onboarding --add-dir /home/vuos/code/p4` (see fundamentals for why: without `--yolo` cmd blocks on command permission prompts and stalls the headless agent)
  - Z.AI: `opencode -m zai-coding-plan/glm-4.7`
- Spread producers across providers by priority: ag-01 → opencode-go, ag-02 → Command Code, ag-03 → Z.AI. Use independent compute per producer.
- Window naming: `23-1`, `23-2`, `23-3`.
- Before sending keys to a window, capture it and check the current state — never assume the previous launch attempt failed or succeeded.

## Inherits

- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, video pipeline, GPU encoding, AgentFS
- [../e022-nautilus-sr-grid/AGENTS.md](../e022-nautilus-sr-grid/AGENTS.md) — example of an honest-failure experiment to feature
- [../e018-hyprframes-browser-video/AGENTS.md](../e018-hyprframes-browser-video/AGENTS.md) — video production reference
