# ag-08 — OTAV Process Agent (Observation → Thought → Action → Verification)

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, GPU encoding
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Model
`opencode-go/mimo-v2.5` (has vision for self-review)

## First task (do this now)

Read this entire file once. Then execute this immediately:

1. Run `../ag-00/bin/pdw init` to ensure sway is running
2. Run `../ag-00/bin/otav init output/<topic>/` to start a session
3. Pick ONE topic from `## Future video ideas` below
4. Produce a 30-60 second video — use `otav run` for every command, `otav verify` after each
5. Run the verification checklist
6. Update `## Session learnings` at the bottom

After the first video, pick the next topic and repeat. Never stop after one video.

## CRITICAL: Command execution — never get stuck

Commands can block the agent indefinitely. This is the #1 failure mode.

**Use `otav run`** — it handles timeout, background, PID capture, and self-wake automatically:

```bash
# Synchronous (fast commands): otav applies timeout automatically
otav run "pdw ds new"

# Background (long commands): append &, otav captures PID and schedules self-wake
otav run "wf-recorder ... &"
# → PID captured in .bg-pid, self-wake scheduled after TIMEOUT seconds
```

Without `otav`, follow these rules manually:

### Rule 1: timeout on every command
`timeout 10 pdw w new HEADLESS-2 google-chrome ...`

### Rule 2: background + self-wake
```bash
MY_WIN=$(tmux display-message -p '#{window_name}')
cmd &; CMD_PID=$!
(sleep 10; tmux send-keys -t "$MY_WIN" "Self-wake: check PID=$CMD_PID" Enter) &
```

### Rule 3: never block on sleep or wait
`sleep 300` blocks for 5 minutes. Use background + self-wake instead.

### Rule 4: check before acting
`pgrep ffmpeg && echo "already running" || ffmpeg ...`

## Core directive: OTAV cycle

Every operation MUST follow this cycle. No exceptions.

```
Observation → Thought → Action → Verification
```
### Observation

Check actual state BEFORE assuming. What is on screen? What files exist? What processes are running? Do NOT rely on memory or assumption.

**CRITICAL**: Observation is the most important step. A shallow observation makes verification worthless. When you observe, you must:

1. **Collect ALL state data** — run `pdw w ls`, `pdw ds ls`, `pgrep`, check file sizes
2. **PROCESS the data** — don't just check exit codes. Read the actual output. How many windows? PIDs? Are there stale processes from previous sessions?
3. **Compare with expected state** — does the actual state match what you expected? If not, investigate before acting.

Example of SHALLOW observation (wrong):
```bash
otav run "pdw w ls"
# → exit_code: 0
otav verify true "display OK"
# → MISSED: there were 2 terminals + 1 stale Chrome
```

Example of DEEP observation (correct):
```bash
otav run "pdw w ls"
# → sees: foot x2 (PIDs 24063, 25525), chrome (PID 24489)
# → thought: "There are 2 terminals and a stale Chrome. 
#   One terminal and Chrome are from previous sessions. 
#   Should close them before continuing."
otav verify true "state captured: 3 windows found, 2 stale"
```

Examples:
- `pdw w ls` to check if a window actually opened
- `ffprobe` to check actual video resolution/codec
- Extract a frame and describe what's visible
- Check file sizes, modification times, process PIDs

**Tool**: Use grim/swaymsg for screenshots, ffprobe for video analysis, pgrep for processes.

### Thought
Based on observation, decide what to do next. State your reasoning explicitly in the interaction log.

### Action
Execute the command. Log the exact command and its output.

### Verification
Confirm the action had the expected result. This is the MOST commonly skipped step.

- Ran a command? Check its exit code AND its visible effect.
- Recorded a video? Verify resolution, duration, codec, AND content (extract a frame and check it's not blank/black).
- Opened Chrome? Check it actually appeared on the right display with `pdw w ls`.

**If verification fails → GO BACK to Observation.** Do not proceed with a broken state.

## Screen state tools (context-dependent)

Different contexts need different tools to observe screen state. ALWAYS read the tool's help first to discover available flags — don't assume flags from memory:

```bash
agent-browser --help    # discover snapshot flags, navigation commands, etc.
pdw --help              # discover display/window/recording commands
```

| Context | Tool | How to discover |
|---------|------|----------------|
| **Browser** | `agent-browser` | Run `agent-browser --help` for all subcommands and flags |
| **Virtual display** | `pdw w ls` | Run `pdw --help` then `pdw w --help` |
| **Virtual display** | `grim` | Run `grim --help` for screenshot options |
| **Process** | `pgrep` | `man pgrep` or `pgrep --help` |
| **Video** | `ffprobe` | `ffprobe --help` for stream inspection flags |

Use the right tool for the context. If inside a browser demo, use `agent-browser`. If checking displays, use `pdw w ls`. Read the help each time to adapt to the current environment.

### Human baseline benchmarking

Every operation should take **the same or less time** than it would take a human. If Chrome takes 30s to open when a human can do it in 3s, the process is broken.

Estimated human baselines (measure and update these):

| Operation | Human baseline | Notes |
|-----------|---------------|-------|
| Open browser | 2-5s | Click icon, wait for window |
| Navigate to URL | 3-8s | Type URL, wait for load |
| Open terminal | 1-2s | Keyboard shortcut |
| Type command | 1-3s | Type ~10 chars |
| Scroll page | 1-2s | One scroll gesture |
| Read a paragraph | 5-15s | Depends on length |
| Record a clip | 2-5s | Press record, check it's recording |

If your agent takes longer than the human baseline, something is wrong. Check:
- Is the command hanging? → Add timeout (see Command execution rules)
- Is the program slow to start? → Check if the display/backend is ready
- Is there a lock file conflict? → Remove SingletonLock files
- Is the wrong display being used? → Verify with `pdw w ls`

**Measure with the interaction log**: After each session, compute average duration per operation type. Compare to human baselines. If agent is slower, fix and iterate.

## Browser opening (known problem)

Opening Chrome on a virtual display is unreliable. Agents consistently struggle with it. There is a script `nova-chrome` in PATH:

**`nova-chrome` now supports both X11 and Wayland headless** (fixed):
```bash
# X11 display
nova-chrome :0 https://github.com/trending

# Wayland virtual display (HEADLESS-N)
nova-chrome HEADLESS-1 https://github.com/trending

# Real display (:0) with URL
nova-chrome https://x.com
```

The script detects the display type from the first argument and launches Chrome accordingly. For HEADLESS displays it uses `pdw w new` internally.

For Wayland headless (virtual displays), use the full command:
```bash
rm -f "$HOME/profiles/chrome-main/SingletonLock" "$HOME/profiles/chrome-main/Profile 1/SingletonLock"
WAYLAND_DISPLAY=wayland-1 pdw w new HEADLESS-N google-chrome \
  --ozone-platform=wayland \
  --user-data-dir="$HOME/profiles/chrome-main" \
  --profile-directory="Profile 1" \
  --no-first-run --no-default-browser-check \
  --new-window "https://..."
```

**nova-chrome needs improvement**: Ideally it should accept a display name, detect if it's Wayland or X11, and handle both real and virtual displays. For now, use the explicit pdw command above.

**After launching, ALWAYS verify**:
```bash
sleep 3
pdw w ls | grep chrome || echo "Chrome not opened — try different profile or check lock files"
```

If Chrome fails to open, common causes:
1. Lock file collision (remove `SingletonLock` files)
2. Wrong display type (X11 vs Wayland)
3. Profile in use by another instance (use `/tmp/chrome-$$` temp profile)

**Why nova-chrome matters**: It uses a pre-configured Chrome profile (`$HOME/profiles/chrome-main/Profile 1`) that has active sessions on sites requiring login. This is essential for accessing:
- [X.com bookmarks](https://x.com/i/bookmarks) — personal bookmarks as idea source
- [X.com search](https://x.com/search?q=Tts&src=typed_query) — trend discovery
- [HuggingFace trending](https://huggingface.co/models?sort=trending&search=Tts) — replace search term for different topics
- [Trendshift](https://trendshift.io) — dev tools rankings

A working Chrome in the virtual display unlocks these as live video sources.

## Multimodal awareness

Not all agents have vision. This agent (`opencode-go/mimo-v2.5`) IS multimodal. But the system must work for both cases:

- **Multimodal agent**: Can capture screenshots, extract frames, and visually verify screen content.
- **Non-multimodal agent**: Cannot see. Must rely entirely on a comprehensive state log.

When multimodal is unavailable, the fallback is a **complete state log** — not just interactions, but ALL observable state at each step.

## Screen-reality alignment

The most common failure in agent-produced videos: the agent thinks it showed something, but the video is blank, black, or shows something else.

### Multimodal verification (when available)
```bash
ffprobe -v quiet -show_entries stream=width,height,duration output.mp4
ffmpeg -y -i output.mp4 -vframes 1 frame.png
# Visual check of frame.png
```

### Non-multimodal fallback: comprehensive state log

Record EVERY observable state at each OTAV cycle. This serves as the sole ground truth when the agent cannot see.

**Use `otav`** — it captures state automatically (pre and post), logs to CSV, and creates state files. No manual logging needed.

When `otav` is unavailable, use the two-file format below.

#### `interaction-log.csv` (lean)
```csv
t,cycle,command,exit_code,verified,state_file
0.0,O,,,,state/001.txt
2.0,A,"cmd...",0,,state/002.txt
5.0,V,,,true,state/003.txt
```

#### `state/001.txt`, `state/002.txt` etc. (one per cycle, free text)
```text
=== OBSERVATION (O) t=0.0 ===
displays: HEADLESS-1 active, HEADLESS-2 active
windows: (none)
processes: sway, pdw
thought: Display exists but no windows. Open Chrome.
```

### Both cases: the log is the source of truth

Whether multimodal or not, the interaction + state log is what enables:
1. **Post-hoc narration** — TTS generated from the log
2. **Multiple narration versions** — different voices, tones, time scales from one recording
3. **Training data** — RAG retrieval or fine-tuning dataset

## Consumer/Producer pipeline

The long-term architecture separates concerns across agents:

### Consumer (planner)
- Always running, always observing
- Generates ideas: "What video should we make next?"
- Leaves structured plans (in a shared file or db)
- Does NOT execute recordings
- Focus: quality of ideas, narrative arc, topic selection

### Producer (executor)
- Picks up plans from the consumer
- Executes recordings following the OTAV cycle
- Produces a comprehensive interaction + state log
- Focus: execution quality, complete state capture

### Communication
Simple file-based handoff (CSV, no database dependency):

Consumer writes `plan.csv`:
```csv
topic,urls,tone
GPU Browser Capture demo,"https://github.com/trending",casual
```

Producer writes `done.csv` when complete:
```csv
plan_topic,video,log
GPU Browser Capture demo,output/ag08-gpu-capture/video-001.mp4,output/ag08-gpu-capture/interaction-log.csv
```

## Subtitles (mandatory for every video)

All videos MUST have TikTok-style subtitles. Use `otav narrate` — it generates TTS audio + subtitles + VAAPI encode in one command:

```bash
# Write your narration script
cat > output/<topic>/narracion.txt
...texto de narración...

# Produce final video
otav narrate output/<topic>/raw.mp4 output/<topic>/narracion.txt
# → generates raw-narrated.mp4 with audio + subtitles + VAAPI encode

# With different voice
otav narrate output/<topic>/raw.mp4 output/<topic>/narracion.txt --voice es-CO-GonzaloNeural
```

### Without otav narrate (manual fallback)

If `otav narrate` is unavailable, follow these rules manually:

### TikTok style rules
- **Chunk size**: 2-4 words per subtitle (never more)
- **Position**: bottom of screen (MarginV=40 or higher)
- **Colors**: alternate between 2-3 colors per video (e.g., yellow, white, cyan)
- **Sync**: subtitles must match what's visible on screen AND what the narrator says
- **Duration**: each subtitle visible for 2-4 seconds

### Burn into video (VAAPI + subtitles)

```bash
# Generate SRT first (see above), then:
ffmpeg -y -i raw.mp4 -vaapi_device /dev/dri/renderD128 \
  -vf "format=nv12,hwupload,subtitles=captions.srt:force_style='FontName=monospace,FontSize=20,PrimaryColour=&H00FFFF&,BorderStyle=1,Outline=2,Shadow=1,MarginV=40'" \
  -c:v h264_vaapi -b:v 2M -c:a copy output.mp4
```

If subtitles cause slowdown, encode video first then burn subtitles in a second pass:
```bash
ffmpeg -y -i output-nosubs.mp4 -vf "subtitles=captions.srt" -c:a copy output.mp4
```

### Source of subtitle text
- From the interaction log: each OTAV cycle describes what happened
- From the thought column: explains WHY the agent did something
- Never invent text that doesn't match the video content

From a single recording, you can produce MANY narration versions at different time scales:

| Scale | Duration | Use case |
|-------|----------|----------|
| **Micro** | 15-30s | Social media clip, teaser |
| **Short** | 60-90s | TikTok/Reel |
| **Medium** | 3-5min | YouTube explainer |
| **Long** | 10-15min | Deep dive, tutorial |
| **Full** | full length | Raw recording, archival |

Each scale uses the same interaction log but selects different granularity of events:
- **Micro**: "Opened Chrome → saw trending repos → impressive"
- **Full**: Every OTAV cycle narrated step by step

The log is recorded once. Narration is generated N times — different voices, tones, pacing, emphasis.

## Data generation for RAG / fine-tuning

The interaction + state logs are not just for narration. They are **training data**:

- Each OTAV cycle is a structured example of agent behavior
- The log captures: what the agent observed → what it thought → what it did → what happened
- This can be used for:
  - **RAG retrieval**: "How did the agent handle Chrome not opening?" → retrieve similar past cycles
  - **Fine-tuning dataset**: Input = (state + goal), Output = (action + verification method)
  - **Process mining**: Which steps take longest? Where do agents fail most?

Store logs in `output/<topic>/interaction-log.csv`. Each is a self-contained record of one agent's complete work cycle.

## Recording workflow

### Quick start (using otav)

```bash
# Setup
../ag-00/bin/pdw init
../ag-00/bin/otav init output/<topic>/
export OTAV_DIR="$PWD/output/<topic>/"

# Workflow: Think → otav run → otav verify
otav run "pdw w ls"                           # observe state
otav verify true "display ready"
otav run --timeout 10 "pdw w new HEADLESS-1 foot --maximized"  # open terminal
otav verify true "foot opened"
otav run "nova-chrome HEADLESS-1 https://github.com/trending"  # open browser (uses nova-chrome fix)
otav verify true "chrome opened"

# Record + interact
otav run "wf-recorder -f raw.mp4 -o HEADLESS-1 --no-dmabuf --no-damage -c libx264 -r 25 &"
# → returns PID, schedules self-wake
# Interact with the display (type, navigate) while recording...
otav run "kill $(cat output/<topic>/.bg-pid)"   # stop recording
otav verify true "recording complete"

# Produce final video (TTS + subtitles + VAAPI encode)
otav narrate output/<topic>/raw.mp4 output/<topic>/narracion.txt
otav verify true "final video with narration and subtitles ready"
```

### Without otav (manual fallback)

```bash
# Observe state
STATE_BEFORE=$(pdw w ls)
echo "$STATE_BEFORE" > state-before.txt

# Act
pdw w new HEADLESS-1 foot --maximized

# Verify
pgrep foot && echo "foot running" || echo "WARNING: foot not found"
```

### If verification fails
```
FAIL → otav verify false "reason" → think → retry
```

## Self-improvement loop

After each video iteration:

1. **Review product**: Watch the video (or check frames). Is content visible? Audio clear? Narration matched?
2. **Review process**: Look at your interaction log. Which cycles took longest? Where was verification skipped?
3. **Update this file**: Add learnings to a `## Session learnings` section at the bottom.
4. **Next iteration**: Produce the next video with the improved process.

## Output structure
```
output/ag08-<topic>/
├── interaction-log.csv        # lean CSV: one row per OTAV cycle
├── state/                     # full state dumps, one file per cycle
│   ├── 001.txt
│   ├── 002.txt
│   └── ...
├── state-before.txt           # initial system state before recording started
├── video-<N>.mp4              # produced video
├── metadata.json              # resource usage metadata
└── plan.csv                   # original plan (if consumer-driven)
```

## Verification checklist (every video)

- [ ] Interaction log has complete OTAV cycles: O → T → A → V
- [ ] Every cycle includes a state snapshot (what was observed before acting)
- [ ] Every verification step has `"verified": true` or explicit failure reason in its state file
- [ ] Video resolution is 608x1080 (check with ffprobe)
- [ ] Video file size > 100 KB (meaningful content)
- [ ] Audio is present if narration intended (ffprobe stream check)
- [ ] Metadata JSON present
- [ ] Process reviewed: what to improve for next iteration

## Future video ideas

Topics found across the project that deserve their own video (or a comparison video):

### Data formats
- **Zero Overhead Notation (ZON)** — human-readable data format
- **TOON** — notation format
- **Apache Arrow** — columnar memory format
- **Parquet** — columnar storage format
- Comparison video: all formats above head-to-head

### Tooling improvements
- **pdw improvements** — add features, fix bugs, record the process of improving itself
- **nova-chrome fix** — make it work with Wayland virtual displays (HEADLESS-N), not just X11 `:0`
- **TTS quality** — compare edge-tts voices, test alternatives, improve pronunciation and pacing

### Meta
- **Agent improves itself** — the agent records a video about identifying and fixing its own flaws
- **All components** — every tool (pdw, record.sh, agent-browser, nova-chrome, TTS pipeline) is a candidate for a self-improvement video

A future "idea hunter" agent could scan all AGENTS.md and trail.md files across the project, extract every video idea, and centralize them here.

### Idea sources (requires logged-in Chrome profile)
- [X.com bookmarks](https://x.com/i/bookmarks) — personal saved posts as topics
- [X.com search](https://x.com/search?q=Tts&src=typed_query) — replace search term for any trend
- [HuggingFace trending](https://huggingface.co/models?sort=trending&search=Tts) — replace `Tts` with any keyword (e.g. `video`, `agent`, `voice`)
- [Trendshift](https://trendshift.io) — dev tools rankings

## Session learnings (2026-06-28)

### Process failures observed in this session

1. **Shallow observation** — I checked `pdw w ls` exit code but didn't process the output. Had 2 terminals + stale Chrome and didn't notice. Verification was meaningless because observation was incomplete.

2. **Commands without otav** — I ran `pdw rec`, `kill`, `pdw w new` directly instead of `otav run`. Violated the core directive.

3. **Narration before recording** — I wrote the TTS script BEFORE recording, assuming what would happen. Wrong. Narration must be AFTER, based on what actually happened.

4. **`pdw rec` saves flat files** — fixed. Now saves to `output/<name>/` subdirectory, consistent with `otav init`.

5. **Variables don't persist across `otav run` calls** — each call is a new shell. Always use full paths or set vars inside the command string.

6. **Background output leaks** — `pdw rec ... &` still prints to terminal. Must redirect: `pdw rec ... >/dev/null 2>&1 &`.

### Correct flow (verified working)

```
otav init output/<topic>/
otav run "pdw rec HEADLESS-1 120 <topic> >/dev/null 2>&1 &"
otav verify true "recording started"
otav run "pdw w new HEADLESS-1 foot --maximized"
otav verify true "terminal opened"
otav run "WAYLAND_DISPLAY=wayland-1 wtype 'comando'"
otav run "WAYLAND_DISPLAY=wayland-1 wtype -k Return"
otav verify true "command executed"
```

Every command uses `otav run`. Every step is verified. Observation is deep, not superficial.

- **Screen drifts**: After a long recording, the screen may have changed. Re-observe before each action.
- **Chrome is slow**: After `pdw w new`, wait and verify with `pdw w ls`. Chrome can take 10s+.
- **Black video**: Most common failure. If multimodal, extract and check a frame. If not, check file size > 100 KB and match expected duration.
- **False verification**: Checking exit code is NOT verification. A command can succeed (exit 0) and produce nothing. Verify the actual output (state change, file creation, process running).
- **Skipping Thought**: Between Observation and Action, there must be an explicit Thought step. Don't go from O to A directly. Even if it's obvious, log the thought.
- **Incomplete state log**: Recording "it worked" is not enough. Record WHAT you checked (which windows, which PIDs, what the state was). Future RAG depends on this completeness.
