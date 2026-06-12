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

### 5. Strategy tension

Big vision (configurable real-time video platform) vs incremental progress (making simple videos now). Noted risk: over-engineering the perfect system prevents shipping anything. Decision deferred — keep making experiments but document the vision so architecture decisions remain compatible with the long-term goal.

### 6. Configurability variables (complete list)

Collected from all sessions:
- Language (es, en, ...)
- TTS engine (edge-tts, elevenlabs, ...)
- TTS voice (per language/gender)
- Video dimensions (9:16 TikTok, 16:9 YouTube, custom)
- Subtitle style: colors, position, font size, split granularity
- Layout: single window, split-screen, overlay, picture-in-picture
- Script type: scripted (precise) or exploratory (reactive narration)
- Capture region: full screen, specific window, tiled windows
