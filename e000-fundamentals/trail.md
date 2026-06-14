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

### 9. OpenCode UI note: background commands

When a command is sent to background (`&`), OpenCode's UI still shows a spinner as if the command is active. This is cosmetic — the command is truly in background. When the self-wake message arrives (`(sleep N; tmux send-keys ...) &`), it may show as `QUEUED` briefly (1-3s) before being processed. This is normal OpenCode behavior, not an error.

### 10. Video refinement roadmap (after e002)

Next iterations for the avatar podcast video:

1. **TTS**: improve Colombian voice quality
2. **Subtitles**: replicate exact TikTok style (font size, word count per chunk, color timing)
3. **Avatars**: multiple camera angles (close-up on active speaker, two-shot, split), like a real podcast
4. **Capture**: fix x11grab on Weston (use `--write-movie` or `--backend=x11`) for PNG-less GPU pipeline
5. **Scale**: produce many variations from the same source content (different angles, subtitle styles, TTS voices)
