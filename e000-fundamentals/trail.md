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
