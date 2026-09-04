# Design trail

This file records design decisions and session history for the p4 multi-agent file-based system.

---

## 2026-06-12 — Initial session

### Decision: Directory naming

Use `e<NNN>-<short-name>/` format (e.g., `e001-test-agentsmd/`) instead of timestamps. Short codes are cleaner and more readable.

### Decision: Agent subdirectories

Each experiment contains `ag-01/`, `ag-02/`, etc. for each agent. Each agent defines its own internal structure.

### Decision: Nested AGENTS.md

AGENTS.md files at every level (root, experiment, agent, sub-agent) act as the communication bus. Agents read the file in their current directory to understand context. There is no message broker, database, or orchestrator — the filesystem is the system.

### Discussion: Skills vs AGENTS.md

Considered using Open Code's native skill system (`.opencode/skills/<name>/SKILL.md`) alongside AGENTS.md. Rejected because:
- It adds cognitive load for the user ("should this be a skill or an AGENTS.md?")
- Skills are flat and non-hierarchical
- AGENTS.md is portable to any agent (Claude, GPT, Cline, etc.)
- The hierarchy of AGENTS.md is the core feature of the system

**Conclusion**: AGENTS.md only. No skills.

### Decision: No authoritative root

The root `p4/AGENTS.md` is minimal — just an index pointing to `e000-fundamentals/`. There is no single source of truth. `e000-fundamentals/` is just another experiment that happens to define conventions by convention, not by authority. Other experiments can ignore or override it.

### Discussion: How agents discover context

Agents don't automatically read nested AGENTS.md files. They only read the one in their current directory. Links can be used for navigation, but the agent must decide what is relevant based on the task. This is intentional — it keeps context small and focused.

### Decision: Language

User dictates in Spanish. All files, code, and agent responses are in English.

### Decision: trail.md

A `trail.md` file in `e000-fundamentals/` records design conversations and decisions. Referenced from the root AGENTS.md so agents can read it.

### Decision: No /tmp

Agents must work inside their own directory, not `/tmp`. Violated once during e001; corrected after review.

### Decision: Video guidelines

- Use `edge-tts` with Colombian voice (`es-CO-GonzaloNeural` or `es-CO-SalomeNeural`). Not espeak-ng.
- Capture real display (`DISPLAY=:0`), no CPU rendering.
- Disable screen lock before recording (`xset`, `xscreensaver-command`, fallbacks).
- 9:16 vertical format, capture 608x1080 region at `+656,0`.
- Terminal font: Monospace 22pt, geometry 46x45.
- Subtitles: TikTok-style (short 2-4 word chunks, alternating colors, bottom position).
- Verify result: no black frames, audio present, narration matches.

### Decision: Agent principles

- Quality over speed.
- Don't assume, verify (read → think → act → check).
- Use your working directory (not /tmp).
- All commands need timeouts.
- Blocking commands go to the background.

### Decision: Structure

```
p4/
├── AGENTS.md                 ← index, points to e000-fundamentals
├── e000-fundamentals/
│   ├── AGENTS.md             ← shared conventions
│   └── trail.md              ← design decisions
├── e001-test-agentsmd/
│   ├── AGENTS.md             ← experiment description
│   └── ag-01/
│       ├── AGENTS.md         ← process that worked
│       ├── script.md          ← narration script
│       ├── subtitles.srt     ← TikTok-style captions
│       └── video.mp4         ← final output
└── ...
```

### Decision: Opaque agent directory names

Two approaches were considered for organizing agent directories:

**Approach 1 — Directory name is metadata**
```
e001/es/tiktok/9x16/ag-01/
e001/en/youtube/16x9/ag-01/
```
Variables encoded in the path. Self-documenting, but deep nesting, renaming cascades, and every new variable forces a tree restructure.

**Approach 2 — Directory is opaque, AGENTS.md is the description**
```
e001/ag-01/   ← AGENTS.md: "es, TikTok, 9:16, subtitled"
e001/ag-02/   ← AGENTS.md: "en, YouTube, 16:9, no subtitles"
```
Variables live in content, not structure. Agent names are stable handles. Adding a new variable (caption style, voice, etc.) never changes the directory tree.

Chosen: **Approach 2**. Key insight: if an agent changes direction mid-work or another agent references it, having metadata in the path creates cascading renames across multiple files. A single AGENTS.md is the one place to update. Stable names survive the project evolving.

### Decision: Github

Repository at `github.com/g8d3/p4`. All changes pushed incrementally.

---

### Decision: Session recovery

If an agent must be killed (stuck, lost context), recover via OpenCode's built-in session system instead of a fresh launch:

1. Find the last session ID from the DB:
   ```bash
   sqlite3 ~/.local/share/opencode/opencode.db \
     "SELECT id FROM session WHERE directory LIKE '%<agent_dir>%' ORDER BY time_updated DESC LIMIT 1;"
   ```
2. Restore: `opencode -s <session_id>` (from the agent's directory)
3. The agent resumes with all previous context intact.

No custom checkpoint files needed. Also supports forking (`opencode -s <id> --fork`).

### Decision: System name

Chosen: **AgentFS** (Agent File System). Alternative: DirChain, FileBus, FolderNet.

---

## Forward plan — recorded 2026-06-12

### 1. GPU-accelerated screen recording

Current approach uses `ffmpeg -f x11grab` (CPU-based). For real-time recording and multiple simultaneous video generation, need GPU-based capture (VAAPI, NVENC, or similar). Research: whether `ffmpeg` with hardware encoding can capture multiple screen regions concurrently at real-time speed.

### 2. Smarter subtitle splitting

Current: fixed number of chunks per audio section → produces awkward breaks (e.g., "una base de datos ni un bus / de mensajes ni un orquestador"). 

Fix: split at natural phrase boundaries (commas, periods, conjunctions) instead of word counts. Each subtitle should be a complete thought fragment.

### 3. Configurable real-time video rendering (big idea)

Instead of pre-rendering videos, build a system where:
- Client receives minimal payload (markdown script, TTS audio, layout config)
- Client renders video in real-time (game-engine style)
- User can configure: dimensions, caption colors/position, layout (split-screen, overlay, PiP), TTS voice, language, font size
- Multiple variations generated from one source without re-recording

This is a large project. Approaches:
- **Web-based**: HTML + CSS + JS rendering, recorded via MediaRecorder API
- **Native**: custom renderer using GPU (WebGPU, OpenGL)
- **Hybrid**: server sends assets, client composes

### 4. Social media integration problem

Current platforms (YouTube, X.com, TikTok) are closed gardens with complex auth and API restrictions. Automating content upload is fragile. 

Alternative vision: build an open agent-friendly platform where agents can post content freely without authentication barriers — a social network for and by agents.

### 5. Strategy tension — resolved

Both approaches are **two phases of the same system**:

**Phase 1 — Pre-rendered (agents)**
Agents produce videos with variations. The human observes how agents plan, what works, what doesn't. This is learning for both human and system. Each video is a data point.

**Phase 2 — Configurable real-time**
A human (or another agent) takes an existing video and tweaks it: avatar, tone, duration, TTS. Each correction is versioned. The system learns: "for this topic, avatar + casual tone performs best".

Both phases run simultaneously. Pre-rendered videos feed the configurable system with templates. The configurable system provides fast human feedback that improves the next generation of pre-rendered videos.

### 6. Versioned human feedback

Each correction a human makes to a video is a training datum:
- Original parameters → corrected parameters
- Over enough corrections, the agent learns which parameters to use for each topic/audience without human intervention

This requires a versioning system for video configurations (not just the video file itself). Storing the config as a JSON/yml alongside the video, tracked in git.

### 7. Avatar and audience variables

Added from user feedback (family review of e001 video):
- **Comprehensibility**: "too niche, hard to understand" → need variations for different audiences
- **Avatar**: use a speaking avatar (podcast-style) instead of raw screen capture
- **Examples**: apply the concept to everyday situations rather than abstract internals
- **Audience targeting**: define audience before generating (developers vs general public vs investors)

### 8. Configurability variables (complete list — updated)

Collected from all sessions:
- Language (es, en, ...)
- TTS engine (edge-tts, elevenlabs, ...)
- TTS voice (per language/gender)
- Avatar (yes/no, style, position)
- Video dimensions (9:16 TikTok, 16:9 YouTube, custom)
- Subtitle style: colors, position, font size, split granularity
- Layout: single window, split-screen, overlay, PiP, avatar+screen
- Script type: scripted (precise) or exploratory (reactive narration)
- Capture region: full screen, specific window, tiled windows
- Audience level: technical, general, executive
- Example style: abstract vs real-world vs storytelling

### 9. GPU-direct video capture options (no CPU, no disk)

Ways to go from GPU framebuffer → H.264 MP4 without intermediate CPU or disk writes:

| Method | GPU render | GPU encode | Disk | Status |
|---|---|---|---|---|
| Godot `--write-movie` + VAAPI re-encode | ✅ | ✅ | ~200MB AVI | ✅ En uso |
| Display real `:0` + x11grab + VAAPI | ✅ | ✅ | 0 | ✅ Funciona (e001) |
| Weston `--backend=x11` + x11grab + VAAPI | ✅ | ✅ | 0 | ✅ Funciona (ag-07) |
| Weston headless + pipewire + wf-recorder | ✅ | ✅ | 0 | ❌ No instalado |
| KMS/DRM direct capture + VAAPI | ✅ | ✅ | 0 | ❌ No explorado |
| Godot + frames.raw + VAAPI | ❌ CPU | ✅ | 17GB | ❌ Descartado |
| Godot `--write-movie` alone | ✅ | ❌ CPU MJPEG | ~200MB | ✅ Pero CPU |

Optimal: Weston `--backend=x11` or display real → 0 disk, 0 CPU. Next to try: pipewire/wf-recorder.

### 10. OpenCode UI note: background commands

When a command is sent to background (`&`), OpenCode's UI still shows a spinner as if the command is active. This is cosmetic — the command is truly in background. When the self-wake message arrives (`(sleep N; tmux send-keys ...) &`), it may show as `QUEUED` briefly (1-3s) before being processed. This is normal OpenCode behavior, not an error.

### 10. Video refinement roadmap (after e002)

Next iterations for the avatar podcast video:

1. **TTS**: improve Colombian voice quality
2. **Subtitles**: replicate exact TikTok style (font size, word count per chunk, color timing)
3. **Avatars**: multiple camera angles (close-up on active speaker, two-shot, split), like a real podcast
4. **Capture**: fix x11grab on Weston (use `--write-movie` or `--backend=x11`) for PNG-less GPU pipeline
5. **Scale**: produce many variations from the same source content (different angles, subtitle styles, TTS voices)

---

## 2026-06-17 — e006 live streaming design

### Decision: New experiment (e006) for live streaming

Streaming en vivo es un pipeline distinto a grabación off-line (e003/e004/e005). Requiere:
- Bitrate constante (CBR) limitado por upload
- Latencia < 2 segundos
- Ring buffer para "últimos N segundos"
- Protocolo de red (RTMP/SRT)

### Decision: Single encoder, dual output

No duplicate VAAPI encoder instances. The Barcelo (8 CU) has limited encoding resources. Use ffmpeg tee muxer or OBS to split one encoded stream to both RTMP and ring buffer.

### Decision: Ring buffer in RAM

"Last N seconds" = circular buffer in RAM. At 1080p60 CBR 6Mbps, 5 minutes = 225 MB. Trivial with 15 GB RAM.

### Open questions for e006

1. Streaming platform (Twitch, YouTube, Owncast)?
2. Capture method (DMA-BUF via Sway or x11grab via Xvfb)?
3. Vertical (608x1080) or horizontal (1920x1080)?
4. Audio source (TTS, mic, system)?
5. Ring buffer trigger (CLI, hotkey, API)?
6. OBS or pure CLI (ffmpeg tee)?

---

## 2026-06-17 — e007 agent self-documentation

### Decision: Record all, cut later

Recording is continuous (no pause/resume). Post-production handles:
- Fast motion for boring segments
- Narration from log
- Table/graph overlays
- Final composition

This keeps the agent simple (just work + log) and the intelligence in the post-production script.

### Decision: Two agents, one pipeline

- ag-01: self-recording agent (records itself researching TTS)
- ag-2: interaction-to-video agent (converts chat logs to video)

Both share: DMA-BUF capture, VAAPI encoding, edge-tts, 608x1080 vertical, post-production ffmpeg pipeline.

### Decision: Vertical format for TikTok

608x1080 (9:16). This is the format already used in e004/e005.

### Key design insight

The agent does NOT control the recording rhythm. It just works and logs. Post-production decides what's fast, what's normal, what gets narration. This separates concerns cleanly.

### Resources checked

Available on system:
- edge-tts 7.2.8 (es-CO voices)
- wf-recorder (DMA-BUF capable)
- h264_vaapi (AMD VAAPI)
- ydotool (Wayland input)
- matplotlib 3.10 + pandas 2.3 (data viz)
- google-chrome (web research)
- ffmpeg with drawtext, overlay, concat filters

### Pain point: concurrent agent capacity

The user needs to know how many agents their AI inference provider can handle simultaneously. This is critical for:
- Running ag-01 + ag-02 in parallel
- Scaling to multiple content agents
- Streaming while agents work

There is a proxy in the p3 directory that can help measure this. TODO: investigate and document actual limits before launching multiple agents.

---

## 2026-06-23 — Session: filex CRUD + e010 agent launch

### Decision: Filex PUT, MKCOL, DELETE, MOVE, rename

Added full CRUD to filex (`~/code/filex/serve_md.py`):
- `do_PUT` — create/overwrite files (with parent dir auto-creation)
- `do_MKCOL` — WebDAV mkdir
- `do_DELETE` — delete files (recursive for dirs)
- `do_MOVE` — WebDAV rename/move (with `Destination` header)
- `?raw=1` — get raw file content for text/code/md files

GUI buttons in toolbar: +📁 create dir, +📄 upload file, 🗑 delete current. Modal rows have ✏️ rename and 🗑 delete per item.

### Decision: Provider vs model distinction

Three active **provider subscriptions** (not just models):

| Provider | ID prefix | How configured |
|----------|-----------|----------------|
| OpenCode Go | `opencode-go/` | `OPENCODE_GO_API_KEY` env var |
| Xiaomi Token Plan | `xiaomi/` | `XIAOMI_API_KEY` env var |
| Z.AI Coding Plan | `zai-coding-plan/` | `/connect` credential |

Each provider has its own compute. To maximize token throughput, launch agents with different providers:

```bash
opencode -m opencode-go/mimo-v2.5          # agent 1
opencode -m xiaomi/mimo-v2.5               # agent 2
opencode -m zai-coding-plan/glm-5.1        # agent 3
```

### Decision: Listing models

Use `opencode models [provider]` to discover available models per provider. This is more reliable than maintaining a static list.

### Decision: CLI model format

The model format is always `provider-id/model-id`. Provider IDs discovered via `opencode providers` and `opencode models`. Examples:

- `opencode-go/deepseek-v4-flash`
- `opencode-go/mimo-v2.5` (vision)
- `xiaomi/mimo-v2.5` (vision)
- `zai-coding-plan/glm-5.1`
- `zai-coding-plan/glm-5v-turbo` (vision)

### Env vars added

- `XIAOMI_API_KEY` — API key for Xiaomi Token Plan
- `XIAOMI_BASE_URL` — base URL for Xiaomi Token Plan

### Decision: Xiaomi regional variants

Xiaomi Token Plan has 3 regions. Each has a separate provider prefix:
- `xiaomi-token-plan-sgp/` — Singapore (use this one, lowest latency)
- `xiaomi-token-plan-ams/` — Amsterdam (Europe)
- `xiaomi-token-plan-cn/` — China

### Decision: Z.AI model tier selection

Z.AI Coding Plan has a **5-hour rolling credit window**. Higher models (glm-5.1) deplete faster. Rule: default to `zai-coding-plan/glm-4.7` for daily production; reserve 5.1 for final polish. Measure actual credit burn before assuming.

### Decision: Always source env vars before launching

```bash
. ~/.zshrc; cd <dir> && opencode -m <provider/model>
```
New tmux windows don't inherit updated env vars unless the shell config is re-sourced.

### Decision: Security — never hardcode API keys

Hardcoded keys in AGENTS.md (or any tracked file) get committed to git. If pushed, they're on GitHub permanently. Always use env vars. If leaked, revoke immediately and scrub git history with `git filter-branch` + force push.

### Lesson: Check before killing agents

Agents may have produced work or been fixed by the user. Always verify pane content and output files before killing and relaunching. Killing wastes tokens and progress.

### Video metadata requirement

Every agent must produce `./output/metadata.json` with: duration, resolution, display type, capture method, encoding, audio/subtitle flags, CPU/GPU/RAM stats, narration voice, recording timestamps. This enables tracing errors and comparing production efficiency across agents.

### Subtitles required

All videos must have TikTok-style subtitles (short chunks, alternating colors, bottom position, 2-4 words per chunk).

### Wayland only, no Xvfb

Use Sway (Wayland headless) for virtual displays. No Xvfb.

### Agent must be reactive, not scripted

ag-01 generated a bash script, executed it, and narrated over the recording. This is WRONG. The agent must think and react in real-time like a human teacher — explain what it's doing AS it does it, respond to system output, show decision-making. A pre-recorded script with voiceover is not an agent video, it's a slideshow.

### Video must have narrative structure

Every video needs: intro (what/why), body (the work with live reasoning), conclusion (findings + call to action / cliffhanger). Without structure, the viewer doesn't know why they're watching.

### Synchronized narration + visuals

What is said must match what is shown. Showing htop without explaining what you're looking for is noise. Every visual needs context: "I'm checking CPU because the previous task was IO-bound" not just "here's htop".

### Human pacing

Agents work at super-human speed. Video must be cut/paced for human reading speed. Don't flash information faster than a person can process.

### All agents must follow these video rules

This applies to ag-01, ag-02, ag-03, and future agents. Video quality = reactive + structured + synced + paced.

### Self-review of process, not just product

Agents must reflect on their own process after each video:
- What took long? What failed? What was unexpected?
- Update their own AGENTS.md with learnings
- This creates a self-improvement loop: each iteration encodes the previous mistakes into better instructions

### Process review is also video content

The reflection process itself is valuable video material. An agent explaining "this time I wasted 5 minutes because I forgot to start sway, so I added a checklist to my AGENTS.md" is both useful for viewers AND improves the system.

---

## 2026-07-01 — AGENTS.md compression consideration

AGENTS.md is 662 lines and growing. Future thought: extract procedural sections
(Chrome/CDP setup, pdw commands, VAAPI encoding) into standalone deterministic
scripts (e.g. `scripts/chrome-cdp.sh`, `scripts/agent-browser.sh`) and reference
them from AGENTS.md. Benefits:
- Reduces token consumption (agents run a script instead of reading prose)
- Deterministic: script behavior is fixed, not reinterpreted
- Testable: scripts can have their own tests

Not urgent now but worth tracking. Threshold for action: ~800+ lines.

---

## 2026-08-06 — e022 Nautilus S/R grid strategy

### Decision: new experiment e022-nautilus-sr-grid

User brief (dictated in Spanish): build and backtest on Nautilus Trader a
**grid strategy** whose levels are placed automatically on support/resistance,
where when a grid order fills, the freed capital moves to the **opposite side**
distributed by a **probability distribution computed from the volume profile**
(user's message was cut at "usando está..." → user chose "Volume profile").

### Decisions

- **Synthetic Gaussian data first** (user choice), regime-switching generator
  (range / trend / downtrend / mixed) so S/R pivots and volume clusters are
  meaningful. Real data (Binance) is a listed next iteration.
- **Nautilus 1.228 pyo3 API**: `BacktestEngine` + `engine.trader` reports.
- **Margin account, OMS netting, synthetic BTC/USDT perpetual** — grid bots
  quote both sides, so a cash account rejects resting sells without inventory.
- **Levels from fractal pivots** (window 3), clustered within 0.10%, gap-filled
  at ATR spacing, within ±1.5% of price.
- **Budget split** ∝ level count per side; **within side** ∝ volume-profile KDE.
- **Fill redistribution pooled once per bar** — the first version resynced all
  opposite-side orders on every fill → 19,642 fills and 20,834 USDT in
  commissions. Batching cut it to ~150-180 fills and <200 USDT.
- **Exposure cap** `max_exposure_budget_mult=1.5` on rebalance placement.

### Results (20k bars, 30k budget, 100k start)

| Regime | Return % | Max DD % |
|---|---|---|
| range | +20.59 | -3.96 |
| trend up | -46.60 | -65.43 |
| downtrend | -234.70 | -234.02 |
| mixed | -0.74 | -10.42 |

### Bug found via timing investigation (2026-08-06, same session)

A timing profile of `engine.run()` exposed that when the exposure cap blocked
both sides, `_rebalance_grid` ran **every bar** (~19k times) because a skipped
rebalance did not update `_last_rebalance`. Two consequences:

1. **Performance**: the backtest took 30.8s instead of ~3.7s and spammed
   ~50k log lines.
2. **Correctness bug**: on skip, `_unallocated = total_budget` re-included the
   base `grid_budget` every bar, compounding the pool to ~292M USDT and
   corrupting the results (made the whipsaw look worse / hid the true edge).

Fixes: caps are now checked **before** cancelling orders (a fully-capped
rebalance is a no-op that keeps the current grid), and rebalance attempts are
throttled by `_last_rebalance_attempt`. Results above are post-fix.

### Second bug: degenerate fractal detection (same session)

`_detect_sr_levels` tested `highs[i] >= np.max(highs[i-w:i+w+1])` where the
window **included the bar itself**, so every bar was always a pivot. Fixed to
compare only against the 2*w neighbours. Effect on results was small (range
+20.6%, trend -46.6%, mixed -0.74% unchanged; downtrend -234.7% → -209.2%)
because clustering and ATR gap-filling dominate level placement anyway.

### Decision: interactive teaching page (user request)

To teach the strategy to a beginner, the user chose an **interactive HTML page**
over a video (dynamic concepts — sliding window, fractal confirmation, KDE
smoothing — are better seen than narrated; mobile-first; offline; zero API
cost). Built `e022-nautilus-sr-grid/interactive/sr-grid-explainer.html`
(vanilla JS + canvas, mirrors the Python strategy, embedded 1100-bar range
slice). Verified with a Node harness (8 rebalances, 91 fills over the slice).

### Findings (honest, documented in the experiment AGENTS.md)

- Fee-efficient per order after batching; real mean-reversion edge in ranging
  markets (**+20.6%**, PF 2.87).
- Destroyed by sustained trends: -46.6% uptrend, **-234% blow-up in downtrend**
  (account goes negative) because fills accumulate inventory between
  rebalances and the exposure cap is only enforced at rebalance.
- Highest-impact next fix: enforce the exposure cap **on fill**, plus a trend
  filter. Then real data and a parameter sweep.

---

## 2026-08-07 — e022 parameter optimization + operational lessons

### What was done

1. **Strategy hardening**: fill-time exposure cap, optional EMA trend filter,
   pool clamp (freed capital that can't be reabsorbed must not re-inflate the
   grid), BTC+USDT inventory tracking (`position_curve.csv`), n_fills and
   total_commissions counters.
2. **Data bug**: the downtrend generator's unbounded drift collapsed price to
   ~1 USDT/BTC (-99.99%). Bounded with a floor/cap (~-55%/+60%).
3. **Search**: `optimize.py` grid-searches 486 configs (span, levels, rebalance,
   exposure cap, trend filter, trend min-dist) on range+mixed, then validates
   top-5 out-of-sample on 3 unseen seeds × 4 regimes.

### Result: a robust config

span=3.5, levels=6, rebalance=96, cap=10x, no trend filter. Training mixed
+50.1%/-10.0% DD. Out-of-sample (3 seeds): range +16.1, mixed +23.8 (min
+5.8), trend +30.3, downtrend +45.6 — all positive, min>0 across every regime.

### The OOS step caught an overfit

span=3.5, levels=6, rebalance=48, cap=10x scored best on training (+54.8%) but
fails OOS (mixed mean -1.9%, one seed -50.5%). Only difference vs robust: the
rebalance interval (48 vs 96). Rebalancing too often overfits training noise.
→ OOS validation is mandatory.

### Caveats documented

Robust config reaches ~314k USDT notional on 100k (~3.1x leverage). Free in sim
(margin_init=0), a liquidation risk in reality. Synthetic trends are cleaner
than real ones, so the trend-fade edge is optimistic.

### Operational lessons (machine froze during the search)

- **BLAS oversubscription froze the laptop**: 8 workers × OpenBLAS all-cores =
  ~96 threads on 12. Fix: force `OPENBLAS_NUM_THREADS=1` etc. + cap workers.
- **Nautilus Rust/pyo3 memory leak**: ~25MB per backtest run. Without worker
  recycling one worker hit ~3GB and the OOM killer killed the search. Fix:
  `max_tasks_per_child`.
- **Transient Nautilus hang**: ~1/50 runs a worker freezes in a futex with no
  CPU (deterministic poison ruled out; faulthandler armed but affected runs were
  clean). Survived via incremental CSV + resume + chunked execution with a
  watchdog that isolates stuck tasks. Root cause still open.
- **Self-wake pattern**: use `(sleep N; tmux send-keys -t <window> "..." Enter) &`
  for non-blocking periodic checks so the agent stays responsive to the user.

---

## 2026-08-12 — e024 Diffusion Studio editor (video editor for coding agents)

### Decision: new experiment e024-diffusion-studio

User wants to play with [diffusionstudio/editor](https://github.com/diffusionstudio/editor)
— an open-source video editor built for coding agents: an agent writes a TSX
composition, the `dapi` CLI mounts it into the editor, and every element stays
editable ("FFmpeg for agents"). This is directly relevant to p4's video
pipeline (compositions as code, browser GPU rendering via WebCodecs,
agent-native CLI conventions).

Decisions:
- **Experiment number**: e024 (next free after e023).
- **Upstream source**: cloned shallow (depth 1, v0.132.0) into
  `e024-diffusion-studio/upstream/`, **gitignored** (23 MB with its own git
  history; not p4's content).
- **Structure**: one full-stack agent (`ag-01`). Initially scaffolded with two
  agents (ag-01 setup+exploration, ag-02 compositions+benchmark), but the user
  (from experience) sees no need for a second agent in a case like this: the
  second agent typically fails from **incomplete context** — the exploration
  phase's findings never fully transfer. Consolidated to one agent that owns
  setup → explore → compose → integrate → benchmark end to end, writing notes
  to `output/exploration.md` so its own context survives across runs.
- **Scope**: evaluate where Diffusion Studio fits in p4's pipeline; the final
  p4 deliverable rule (h264_vaapi) still applies to any ffmpeg assembly, while
  `dapi node render`'s own encoder is an open question to report on.
- **Open questions**: how much needs the hosted backend (Supabase/API) vs
  works offline; whether `dapi node render` can replace the ffmpeg composition
  step; cost/effort of `generate.*` assets.

---

## 2026-08-07 — e022 real-data reality check (the honest end of the road)

After the synthetic "robust config" was found, the user chose to test on real
data. Downloaded Binance BTC/USDT klines (`fetch_binance.py`): 105k 5-min bars
(1y) and 35k 1h bars (4y). Results on 100k start:

| Dataset | Config | Return | Max DD | Fills | Commissions |
|---|---|---|---|---|---|
| 5m, 1y | robust | -20.6% | -48.5% | 13,424 | 25,235 USDT |
| 5m, 1y | defaults | -30.2% | -30.3% | 16,181 | 20,654 USDT |
| 1h, 4y | robust | -79.4% | -94.3% | 6,918 | 7,183 USDT |

### Conclusion

The synthetic "+50%" edge was an artifact of smooth Gaussian regime structure.
On real BTC: 5m is fee-dominated (13-16k fills/year = 20-25% of capital in
commissions) and 1h is trend-dominated (grid accumulates inventory into the
2022 bear / 2023-24 bull). **The strategy, as designed, does not make money on
real data.** This is the single most valuable result of the experiment: it
demonstrates why synthetic backtests alone mean almost nothing and why real
out-of-sample validation is mandatory. Documented in the experiment AGENTS.md
with a redesign list (cut churn, trend protection, realistic fees, liquidation
model).

---

## 2026-08-15 — e028 DeepSeek Harness (dsh web): five traps to LAN access

User asked to run `npx @deepseek-ai/dsh web` (DeepSeek Harness browser UI).
Documented the full journey as a new experiment `e028-dsh-harness/`.

### Trap 1 — npm 12 blocks install scripts → no pty.node

`npx @deepseek-ai/dsh web` crashes: `Failed to load native module: pty.node`.
node-pty ships prebuilds only for darwin/win32; linux must compile at install.
npm 12's `allowScripts` security feature blocked node-pty's `install` script by
default. The npx cache can't be repaired per-package → install into a real
project and approve scripts:

```bash
npm install @deepseek-ai/dsh
npm install-scripts approve node-pty koffi @deepseek-ai/dsh-subprocess-local
npm rebuild node-pty
```

### Trap 2 — dsh refuses LAN binds

`--host 0.0.0.0` → hard error ("expose remote code execution to the network");
any other IP → config validation (only `127.0.0.1`/`0.0.0.0` allowed). LAN
requires a reverse proxy. Bonus surprise: socat cannot bind `0.0.0.0:3080`
while dsh owns `127.0.0.1:3080` (EADDRINUSE, empirically reproducible, not
normal socket semantics) → proxy must use a different port (8080).

### Trap 3 — crypto.randomUUID dies over plain HTTP on LAN

Browser client calls `crypto.randomUUID()`; it only exists in secure contexts
(HTTPS or localhost). LAN HTTP origin is insecure → UI breaks. Fix: socat TLS
proxy (8443) with a self-signed cert.

### Trap 4 — /api 403: the browser-trust fence

dsh validates every `/api` request (Host must be loopback or trusted; Origin
must match). Fix: `dsh web --trusted-host 192.168.0.93:8443` — value must equal
the browser origin exactly (host:port).

### Trap 5 — privileged methods are loopback-only by design

`settings.*`, `credentials.*`, `agentPreset.*`, `host.pickDirectory`,
`host.openPath`, `llm.discoverModels` (dsh-client-connection
`PRIVILEGED_METHODS`) stay 403 on LAN **even with --trusted-host** — the source
is explicit that `trustedHosts` is a DNS-rebinding fence, not authentication.
Not configurable. Only fix: SSH tunnel so the browser origin is loopback.

---

## 2026-08-15 — e029 HTML video explainer ("phone-ai-developer")

User asked for a **video from HTML, as beautiful as possible**, as a
self-explanation for a non-technical Spanish-speaking audience: "look, with an
Android phone + Termux + SSH + a computer you already have an AI
developer/designer working for you" — the real cheap toolkit (OpenCode Go +
DeepSeek Flash). User explicitly wanted to avoid Open Design (too heavy);
web-searched template inspiration became a beat inside the video.

### Decisions

- **Route**: `/hyperframes` → faceless-explainer (no site, no capture; invented
  visuals). Single deliverable = MP4, not a navigable deck.
- **Design**: **Capsule** frame preset (warm cream, 2px ink pills, Bodoni Moda +
  Space Grotesk, candy pastels, grain + radial glows) — playful editorial,
  friendly for non-technical viewers, zero external assets (all CSS/SVG).
- **Spanish narration**: Kokoro local TTS `ef_dora`. Requires a venv
  (`/home/vuos/.hf-venv`) with `kokoro-onnx` + `soundfile`; the CLI honors
  `HYPERFRAMES_PYTHON`. No HeyGen credential → **no BGM** (retrieve-only,
  no offline fallback); local bundled SFX only. Captions skipped (Kokoro has no
  word timestamps).
- **Fonts**: variable fonts Bodoni Moda + Space Grotesk, one latin `.woff2`
  each (downloaded from the Google Fonts CSS API with a modern UA) — the
  `@font-face` lives inside each sub-composition as the contract requires.
- **Subagents unavailable** (only `build` in primary mode) → the 9 frame
  workers ran **inline serially** (the contract's fallback ladder).

### Bugs caught at check time

- `getElementById("#c1")` with a `#` prefix → null → `getTotalLength()` crash
  (frame 03).
- Frame 09's verbs lingering at 55% opacity under the closing pill →
  `content_overlap`; closing must fully retire the verbs.
- Background + grain are both timed clips; both on track 1 → overlap violation,
  grain moved to track 2.
- `.verb` had a CSS `transform: translate(-50%,-50%)` plus GSAP animating `y` →
  `gsap_css_transform_conflict`; moved centering into `xPercent/yPercent`.

### Result

`e029-html-video-explainer/videos/phone-ai-developer/renders/video.mp4` —
**58.3s, 1920×1080, h264**, 9 frames, Spanish voice + SFX, 0 check errors.
Frames 4 & 7 carry dashed "TU FOTO AQUÍ" placeholders for the user's real
photos/videos of Termux and dictation.

### TTS correction (same session, user feedback)

User: "¿por qué Kokoro? pensé que Gemini TTS con las voces preferidas … también
que aprendas Deepgram Flux o Aura … y busques más proveedores de TTS realistas
con emociones en leaderboards / x.com / HuggingFace."

- **Why Kokoro happened**: `audio.mjs`'s provider chain (HeyGen → ElevenLabs →
  Kokoro local) silently fell to Kokoro without a HeyGen credential. The p4
  primary (KIE Gemini TTS with preferred voices) was never wired into the
  HyperFrames audio step — my miss.
- **Fix**: re-voiced the narration with **Deepgram Aura-2 `aura-2-celeste-es`**
  (es-co Colombian, "Clear/Energetic/Friendly"), which is cheaper than KIE and
  has free credits. Re-rendered to `renders/video.mp4` (58.3s). Added
  `bin/dg-tts.sh` (Deepgram wrapper mirroring `kie-tts.sh`).
- **TTS research documented** in `TTS-RESEARCH.md`: Speech Arena / HF TTS Arena
  leaders (Simba 3.2, Qwen-Audio, Gemini 3.1 Flash=KIE, StepAudio; Deepgram's
  own blind test puts Flux #1), and emotion-capable providers — **Fish Audio
  S2.1 Pro** (free-form `[tag]` emotions, 80+ langs, $15/1M, free dev tier),
  **Deepgram Flux** (conversation-native, expressive by default, English-only,
  free through 2026-09-12), Hume Octave 2, ElevenLabs v3, Cartesia Sonic 3.5,
  MiniMax, plus open weights (Orpheus, Chatterbox, IndexTTS-2, CosyVoice3,
  Sesame CSM). Recommendation: Deepgram Celeste for Spanish narration, Fish for
  emotion-heavy marketing lines, Flux for future voice agents.
- **MP3 convention**: p4 does not use WAV. Converted the Deepgram WAVs to MP3
  (`libmp3lame q2`), deleted the WAVs, and updated `dg-tts.sh` to output MP3
  directly (Deepgram's default — no container/encoding params needed; WAV needs
  `encoding=linear16&container=wav`). Note: MP3 container duration includes ~56ms
  LAME encoder delay; the storyboard/frame slots must use the **decoded** duration
  (what `check` measures), not the container duration.

### Transcription correction (same session, user interruption — a real gap)

User interrupted: generated audio **must be transcribed** before anything downstream,
and suggested Deepgram likely has STT models. Correct on both counts — the first pass
dropped captions entirely because Kokoro emits no word timestamps.

- **Deepgram Nova-3** (`/v1/listen?model=nova-3&language=es&smart_format=true`) returns
  `words[]` with `{word, start, end}` — the exact input `captions.mjs` needs
  (`audio_meta.json -> voices[].words`). Confidence ~0.99 on the 9 narration lines.
- **Wired the transcription into the pipeline**: transcribed all 9 MP3s, wrote the 148
  word timestamps into `audio_meta.json`, ran `captions.mjs build` → **66 karaoke caption
  groups** using the Capsule preset skin. Reassembled, re-injected transitions, re-checked
  (38 contrast checks, 0 errors), re-rendered `renders/video.mp4` (58.3s, 9.5 MB).
- **Rule for future video runs**: TTS → **transcribe** (word timestamps) → captions →
  assemble. Never ship a narrated video without transcription (captions are the point of
  word timestamps).
- **`captions.mjs` symlink gotcha**: running it through the `~/.config/opencode/skills/...`
  path silently no-ops (exit 0, zero output, no files) because that dir is a symlink to
  `~/.claude/skills/...` — `process.argv[1]` (symlink) ≠ `import.meta.url` (realpath), so
  the CLI guard fails. Run via the realpath.
- **Font naming for captions**: the caption skin's `@font-face` generator matches font
  files by family-prefix (`bodoni-latin.woff2` → "bodoni…" ≠ "Bodoni Moda" key) — renamed
  to `Bodoni_Moda_400.woff2` / `Space_Grotesk_400.woff2` and updated the frame refs.
- **Added `bin/dg-transcribe.sh`** — reusable Nova-3 STT wrapper (mirrors `dg-tts.sh`).

### Decisions

- **Experiment e028** as a self-contained, reproducible runbook: `bin/install.sh`
  (npm 12 fix), `bin/start.sh`/`bin/stop.sh` (dsh + HTTP/TLS proxies), cert
  generation, verification curls. The working install lives in gitignored `app/`.
- **Working topology**: HTTP 8080 and HTTPS 8443 proxies → `127.0.0.1:3080` for
  non-privileged LAN browsing; SSH tunnel for full functionality from the phone.
- **Security posture documented**: proxies bypass dsh's loopback-only bind, so
  LAN exposure is only for trusted networks; self-signed TLS still MITM-able.



## e033 — VUZA playground (2026-08-18)

Experiment [e033-vuza-playground](../e033-vuza-playground/AGENTS.md): "play with"
[VUZA](https://github.com/AliRash3ed/VUZA-Free-AI-Video-Creator-and-Pinterest-Video-Scraper)
— free faceless-video generator that claims a "world's first free Pinterest
video scraper".

Verified:
- Install + FastAPI web app + REST routes: WORK (Python 3.12 venv, moviepy 2.2.1,
  playwright 1.62, edge-tts 7.2.8).
- **AI brain wired to opencode-go** (`deepseek-v4-flash`) via its OpenAI-compatible
  endpoint — no OpenRouter key needed. Script gen + per-sentence stock keywords work.
- Edge-TTS voiceover + moviepy 2.2 assembly: WORK — produced a 7.6s 9:16 captioned
  video (subtitles + audio). Fixed a real bug first: `ImageClip` re-imported inside
  `create_video()`'s watermark block shadows the module import → photo path raised
  `UnboundLocalError` (one-line fix in `repo/video_engine.py`).
- **Pinterest scraper: BLOCKED.** Headless Chromium gets Pinterest's sign-in modal
  → 0 pins → the headline claim is false out-of-the-box. Scripts `wait_until=
  "networkidle"` often yield an empty body (geo-redirect to co.pinterest.com);
  `"load"` yields real HTML but still the login wall. Needs a signed-in session
  (drive real chrome-main profile via CDP) — documented as next step, not done.
- Pexels/Pixabay need API keys (none present) → return [].

Deliverables: `repo/` (with the fix + `.git` stripped), `bin/test_pipeline.py`,
this AGENTS.md. Uses opencode-go creds instead of OpenRouter; re-encode any kept
video to h264_vaapi per p4 rule.

---

## e034 — Motion Design Skill playground (2026-08-19)

Experiment [e034-motion-design-skill](../e034-motion-design-skill/AGENTS.md): "play with"
[LottieFiles/motion-design-skill](https://github.com/LottieFiles/motion-design-skill) and
**make several animations** with it.

### Findings

- The skill is a self-contained MIT package (80K): `SKILL.md` (8-step checklist, 4 motion
  personalities with duration/easing/overshoot budgets, property table, 1/3 rules) + `director/`
  + `patterns/` + `reference/`. It is implementation-agnostic and maps 1:1 onto HyperFrames
  authoring.
- Produced 5 motion graphics (motion-graphics route, silent, 5.5-8s): playful-card,
  premium-reveal, corporate-dashboard, energetic-hero, state-feedback. All pass
  `hyperframes check` with 0 errors / 0 warnings.
- Joined everything into one demo reel (`output/reel.mp4`): title card (rendered
  `index.html`) + the 5 animations concatenated, re-encoded to h264_vaapi (42s).
- Re-encoded all finals to `h264_vaapi` per p4 rule (`encode_vaapi.sh`); verified encoder tag
  with `stream_tags`.
- Learning: the two skills are complementary — the motion-design-skill supplies the
  *why* (personality, physics, layering), `/hyperframes-core` supplies the *how* (determinism,
  single paused timeline, clip windows, layout/contrast gates). The biggest quality lift was
  the mandatory three layers (primary/secondary/ambient) and table-driven durations/easing.
- Gaps: the skill has no accessibility guidance (HyperFrames' WCAG checker is the stricter gate)
  and no determinism constraints — those come from the framework.

### Render loop

`check`/`lint` only lint the project's `index.html` (no `-c` flag) → validating N standalone
compositions means `cp compositions/<name>.html index.html && npm run check` per file, serially.
Render with `npx hyperframes render -c compositions/<name>.html -o renders/<name>.mp4`, then
re-encode with `encode_vaapi.sh`.

## 2026-08-28 — pi agent + GROQ provider (pi-web)

Fixed GROQ for the pi agent running under pi-web. Root causes: pi sends the system
prompt with `role: "developer"` for reasoning models (GROQ templates reject it →
`400 Unexpected message role`); the built-in groq catalog is stale (two llama models
gone); and the `sync-opencode-models` extension rewrote `models.json` wiping every
non-opencode-go provider on each pi launch / new session.

Changes: `auth.json` groq key; `models.json` groq provider with
`supportsDeveloperRole: false` + custom models; fixed the sync extension to preserve
other providers; added `zz-groq-restore.ts`; pruned `enabledModels`. Discovered
pi-web's session REST API (no auth on localhost:8504) to message/change other
sessions. Remaining wall: GROQ free-tier TPM (~8k/min) vs pi's ~18–24k request →
requires DEV tier for real agent use.

Full write-up, curl repros, the inter-session API trick, and security notes:
[groq-pi-setup.md](groq-pi-setup.md)

## 2026-08-29 — Kaplay game session (e046): verification methodology + hold the "real user path"

Session on creating a Kaplay mobile platformer. Two things worth recording: the
CPU measurement lesson, and a persistent process failure I kept repeating.

### Lesson 1 — headless browser CPU is inherent, not a mistake

The user flagged CPU repeatedly. The honest answer: **agent-browser / headless
Chrome renders via SwiftShader (software, `--enable-unsafe-swiftshader`) because
it has no GPU.** So ANY capture/screenshot made with agent-browser burns CPU by
its own nature. It was not "running it wrong" — it is a property of the tool, and
the only way to measure *the game's* cost is NOT via agent-browser.

Measured with a continuous sampler: opening the browser spiked the Chrome process
to **141%**; closing it returned to **0%**. The game itself sits near 0%.

**Rule:** to judge the real cost of a browser app, either (a) sample over time, or
(b) open it in the desktop browser (GPU), NOT via headless screenshots.

### Lesson 2 — one-shot measurements hide spikes (the real methodology lesson)

I kept reporting "CPU fine" / "jump fixed" based on single `ps` snapshots or a
single `hero.jump()` eval. The user correctly insisted: **register across time**.
A single `ps`/`top` only sees the instant — it misses spikes that rise and fall.
The fix was a continuous sampler: `bin/monitor-cpu.sh` (CSV log + notify.sh push
when a threshold is sustained). This is now the standard for any resource review.

### Lesson 3 — test the REAL user path, not the internal API (the persistent mistake)

This is the one worth internalizing. I diagnosed the jump by calling
`hero.jump(820)` directly — it jumped, so I declared it "fixed." But the user does
not call `hero.jump()`; they **tap a button**. The actual bug was entirely
different: `#btnJump` sat OUTSIDE `.pad` and inherited `pointer-events: none` from
`.touch-controls`, so taps fell through to the canvas. The jump "worked" via the
internal API while being completely broken via the real input path.

**Rule:** when the user reports a symptom ("it doesn't jump", "it doesn't move"),
reproduce it through the SAME path the user uses (button tap, touch, keyboard
event on the visible element), not through an internal function. Verify what the
user sees, not what the code can do when called directly.

### Also fixed this session (e046)

- `#btnJump` not tappable → `pointer-events: auto` on generic `.btn`.
- Touch input now tracked at the DOCUMENT level (tag touches by id) so input never
  sticks when the finger slides off a button ("scenario moves by itself").
- Camera no longer flies up on jump (anchored to ground Y, clamped).
- Adaptive resolution for portrait vs landscape; bigger, legible HUD/menu text.
## 2026-09-03 — ZAI coding plan usage in one call

Check GLM Coding Plan quota directly (don't probe guessed endpoints — `/api/coding/pays/*` 404; docs scraping is slow):

```bash
curl -s https://api.z.ai/api/monitor/usage/quota/limit -H "Authorization: Bearer $ZAI_API_KEY"
```

- `data.level` = plan tier (lite/pro/max)
- `TOKENS_LIMIT` = 5-hour window, `percentage` used; `nextResetTime` epoch ms
- `TIME_LIMIT` = MCP calls/month (1000 on all plans)
- Pro = 12k credits/5h + 60k/week (weekly not exposed by API; console only)

Full usage history: `node ~/.claude/plugins/cache/zai-coding-plugins/glm-plan-usage/0.0.1/skills/usage-query-skill/scripts/query-usage.mjs` (needs `ANTHROPIC_AUTH_TOKEN=$ZAI_API_KEY ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic`).

Lesson: for "what's my X account status" questions, grep locally installed tooling first (`~/.claude/plugins`, `~/.config`) — vendors ship query endpoints in their plugins.

Also: keep answers to simple status questions short — a table plus one command, no process narrative.

Follow-up (same day): fresh agent ignored trail.md and still burned 87.8k tokens / 8 calls re-discovering the endpoint (found it via 9router's hardcoded list). AGENTS.md hints only work if agents choose to read them — promoted the answer to a skill: `.agents/skills/zai-usage/`, which is auto-surfaced in every agent's system prompt. Measured via `~/.pi/agent/sessions/*/*.jsonl` usage fields (the z.ai hourly usage API lags too much for per-agent measurement).
