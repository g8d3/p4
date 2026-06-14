# e000 — Fundamentals

This experiment defines shared conventions and configuration that other experiments can inherit or override.

## Directory naming

Each experiment lives in a subdirectory with the format:

```
e<NNN>-<short-name>/
```

Examples:
```
e000-fundamentals/
e001-test-agentsmd/
e002-...
```

## Agent subdirectories

Within each experiment, each agent has its own directory:

```
e001-experiment/
├── AGENTS.md
├── ag-01/
├── ag-02/
└── ag-03/
```

Each agent defines its own internal structure and may have its own `AGENTS.md`.

Abstraction levels are infinite. An experiment may contain sub-experiments, and an agent may contain sub-agents. Each level inherits context from its parent.

## Nested AGENTS.md

- **`<experiment>/AGENTS.md`**: describes what the experiment does, its files, and how to run it.
- **`<experiment>/ag-<N>/AGENTS.md`**: (optional) agent-specific documentation.

## Working environment

- **Device**: Android + Termux → SSH to Linux (zsh + tmux).
- **Input**: Google Keyboard (voice dictation).
- **Agent**: Open Code CLI.
- **Primary provider**: opencode-go.
- **Secondary provider**: Z.AI (coding plan Pro, not pay-as-you-go).
- **Models**: DeepSeek V4 Flash, Mimo 2.5 (non-Pro, Xiaomi). Mimo 2.5 supports vision/multimodal, ideal for video tasks.
- **tmux**: windows only, no panes.
- **Mobile-first**: all interfaces (terminal or web) must be mobile-friendly.

### Environment variables

| Variable | Description |
|---|---|
| `OPENCODE_GO_API_KEY` | API key for opencode-go |
| `OPENCODE_GO_BASE_URL` | Base URL for opencode-go |
| `OPENCODE_GO_MODEL` | Active model for opencode-go |
| `OPENCODE_API_KEY` | Alias pointing to `OPENCODE_GO_API_KEY` |
| `ZAI_API_KEY` | API key for Z.AI (coding plan Pro) |

## Agent principles

- **Quality over speed**: don't just finish fast. Explore freely but balance it — don't add unnecessary code. Prioritize simple, well-made solutions.
- **Don't assume, verify**: before changing something, read the current state. Then think how to change it, act, and finally verify the result is as expected. Never assume something works without confirming.
- **Use your working directory**: don't use `/tmp` or external directories. Work inside your own directory and keep it organized however you see fit.
- **Command timeouts**: every command must have an estimated timeout. If unsure how long it will take, add a generous margin. Never leave a command without a timeout.
- **Never use pkill without extreme precision**: `pkill -f godot4` kills Godot processes across ALL tmux windows, including other agents. Use `kill $PID` with a specific process ID instead. If you must use pkill, scope it tightly (e.g., `pkill -f "Xvfb :99"`).
- **Blocking commands to background**: if a command is designed to block the terminal (servers, long processes), run it in the background.

## Video recording

- **Verify output**: check that the video is not black, has audio, and narration matches what is on screen.
- **Screen capture**: use the real display (`DISPLAY=:0` or similar), no CPU rendering.
- **Disable screen lock**: before recording, prevent screen lock. Try in order:
  1. `xset s off && xset -dpms`
  2. `xscreensaver-command -exit`
  3. Fallbacks: `xdg-screensaver suspend` or `gsettings set org.gnome.desktop.screensaver idle-activation-enabled false`
- **TTS**: Colombian voice. Use `edge-tts` with `es-CO-SalomeNeural` or `es-CO-GonzaloNeural`. Do not use espeak-ng or generic voices.
- **Mobile format**: record in vertical aspect ratio (9:16). To achieve this:
  1. Select only the relevant window or region (not full monitor).
  2. Resize and reposition windows to fill the capture area efficiently, leaving no wasted space.
  3. Ensure content is readable on a vertical screen.
- **Video types**:
  - **Scripted**: agent follows a predefined script and narrates it as written.
  - **Exploratory**: agent narrates live what it is doing — what it plans, problems it finds, how it solves them, its decisions in the moment. No script, reactive.

## Context inheritance

An agent only reads its own `AGENTS.md`. To share rules across agents, use **explicit inheritance**:

Each AGENTS.md declares what it needs from parent levels in an `## Inherits` section with **real markdown links** (not backticks):

```markdown
## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, GPU encoding
- [../AGENTS.md](../AGENTS.md) — experiment scope
```

The Inherits section is the agent's navigation menu. It both documents context for humans and provides clickable links for filex browsing.

The launch prompt must tell the agent to explicitly read each inherited file:

```
tmux send-keys -t <name> "Read AGENTS.md, then read each file listed in Inherits. Execute the task." Enter
```

This is opt-in: only agents that declare `## Inherits` receive parent context. Others work in isolation.

## Launching interactive agents

To launch an agent for a specific task:

1. Open a new tmux window: `tmux new-window -n <name> -d`
2. `cd` into the agent's directory (where its `AGENTS.md` lives)
3. Start opencode interactively (no arguments):
   ```
   tmux send-keys -t <name> "opencode" Enter
   ```
4. Wait for it to load (~3s), then send the instruction:
   ```
   sleep 3
   tmux send-keys -t <name> "Read AGENTS.md, then read each file listed in Inherits. Execute the task." Enter
   ```

**Important**: `opencode "text"` is NOT interactive — it treats the argument as a directory. Always launch opencode with no arguments, then send the prompt after it loads.

The agent's AGENTS.md + inherited files are its context.

### Model selection

By default agents use DeepSeek V4 Flash. To use a different model, specify it when launching:

```
opencode -m opencode-go/mimo-v2.5
```

The agent's AGENTS.md should declare its required model in a `## Model` section. The orchestrator reads this and uses the corresponding `-m` flag.

Available models: `opencode-go/deepseek-v4-flash`, `opencode-go/mimo-v2.5` (has vision), `opencode/mimo-v2.5-free`, `opencode-go/mimo-v2.5-pro` (avoid Pro).

### Video rendering: CPU vs GPU

There are two fundamentally different approaches:

**Composition (CPU, ffmpeg filters)**
Takes existing assets (images, audio) and joins them with ffmpeg. No screen recording, no display needed. A 4-minute video encodes in seconds — much faster than real time. Ideal for: podcast avatars, slideshows, anything that doesn't need live interaction. Scales to many parallel videos since each is just a CPU process.

**Screen capture (GPU, x11grab / Godot / OBS)**
Runs a live application (terminal, game engine, browser) and captures its display output. Takes exactly real time — a 4-minute demo takes 4 minutes to capture. Captures authentic interaction: mouse movement, 3D animations, terminal typing. Each capture needs a display.

**Scaling with virtual displays**
To produce many videos in parallel via screen capture, use `Xvfb` (X virtual framebuffer) to create multiple virtual displays. Each runs its own Godot/terminal scene, captured by a separate ffmpeg instance — all sharing the same GPU:

```
Xvfb :99 -screen 0 608x1080x24 &
DISPLAY=:99 godot --headless --script render_scene.gd &
ffmpeg -f x11grab -video_size 608x1080 -i :99.0 video.mp4
```

The GPU advantage is not speed per video — it is **parallelism**. One GPU can render 10+ virtual displays simultaneously, while CPU encoding would queue them.

### Cleanup

When an agent completes its task (or is no longer needed), close its tmux window:

```
tmux kill-window -t <name>
```

The orchestrator should check agent status before launching new ones. Running agents consume tokens and may interfere with new tasks.

### Command execution rules

Every agent must apply these to each command they write:

1. **Timeout every command**: `timeout <estimated_seconds> <command>`. If unsure, add a generous margin. Never leave a command without timeout.
2. **Kill by PID, not pkill**: `kill $PID` instead of `pkill -f pattern`. pkill without extreme precision kills processes across all windows.
3. **Background blocking commands**: servers, long renders, watches → run with `&` in the background.

Each AGENTS.md should include a concrete `## Command execution` section with examples relevant to that agent's task.

### Verification

Do NOT assume an agent is working from a single pane capture. The Build mode interface is always displayed — even when idle. To confirm real activity:

1. Capture the agent's tmux pane **multiple times** with 2-3 second intervals.
2. Look for **changing content**: token count increasing, progress indicators, new text output.
3. If the display is identical across 3+ captures, the agent is **idle or stuck** — not working.
4. To check if it finished: look for output files (videos, scripts, etc.) or `done.txt` if the agent creates one.
5. If stuck and no output produced: kill the window and relaunch.

A single capture showing "Build · ModelName · high" is NOT evidence of activity.

### Agent state machine

The OpenCode CLI has 4 states:

| State | Status bar | Tokens | Meaning | Action |
|---|---|---|---|---|
| **Listening** | (blank — no bar) | — | Waiting for user input | Type message + Enter |
| **Working** | `esc interrupt` + spinner | Rising | Agent is processing | Wait. Don't interrupt |
| **Stuck** | `esc interrupt` | Frozen | Command finished but agent looped. Or a command is running longer than expected | Press Escape → Clean. Then send message |
| **Stuck + queued** | `esc interrupt QUEUED` | Frozen | Same as stuck, but someone sent messages while it was stuck. Those messages are queued | Press Escape → Clean. Then send message + Enter. Agent consumes queue → Working |
| **Clean** | (blank) | — | After Escape was pressed. Chat is empty, agent waiting | Send any message + Enter |

**Detecting stuck without QUEUED**: QUEUED only appears if someone sent extra messages. If no messages were sent, the agent can still be stuck — look for unchanged token count for 10+ seconds while status shows `esc interrupt`. In that case, press Escape and send "Continue."

**Escape timing**: Press Escape rapidly (200-300ms between presses). A slow press may not register because the agent processes input at terminal speed. Two quick Escapes in ~500ms total is the safest rhythm.

**Plan mode vs Build mode**: OpenCode has two modes. Plan mode only plans (no commands). Build mode executes. If the agent sees "Plan" in the status bar instead of "Build", it cannot run commands. Press Tab to switch to Build mode before executing. The prompt should always check: "Am I in Build mode?" before starting work.

**Self-wake pattern**: Every command runs in background with `>/dev/null 2>&1 &`. The agent never blocks. A single synchronous command breaks the cycle.

When ALL commands are truly backgrounded and self-wake checks are scheduled, timeouts become redundant. The agent checks progress at each wake and decides based on context (is the output file growing? GPU active? Errors?) whether to wait, kill, or retry. This is smarter than a fixed timeout.

```bash
# Bad — agent blocks
timeout 600 godot4 ...

# Bad — self-wake without context
(sleep 30; send-keys "Check progress" Enter) &

# Good — self-wake with full context
RENDER_PID=$!
(sleep 30; send-keys "Self-wake: PID=$RENDER_PID, step=2/4 Godot render. Check if running, check for errors in output, check if done.txt exists." Enter) &

# Agent continues working here — read files, write code, plan, launch more background commands.
```

The self-wake message must include enough context for the agent to act immediately: which PID, which step, what to look for, what to do next. Without this, the agent has to re-read previous context to remember what it was doing, wasting time and tokens.

**Agent script transparency**: To make stuck detection easier, agents should print progress markers in their scripts:

```bash
echo "=== STEP 1/4: Starting Weston ==="
weston ...
echo "=== STEP 2/4: Starting ffmpeg capture ==="
ffmpeg ...
echo "=== STEP 3/4: Running Godot ==="
godot4 ...
echo "=== STEP 4/4: Encoding final video ==="
ffmpeg ...
echo "=== DONE ==="
```

This way the orchestrator can see which step is currently executing and estimate if it's taking too long.

## Language

- User dictates in Spanish.
- All files, code, and agent responses are written in English.

## GPU encoding (VAAPI)

This AMD GPU supports VAAPI hardware encoding. Use:

```
export LIBVA_DRIVER_NAME=radeonsi
ffmpeg -vaapi_device /dev/dri/renderD128 -i input_frames -vf "format=nv12,hwupload" -c:v h264_vaapi output.mp4
```

Key: `-vf "format=nv12,hwupload"` is required before the VAAPI encoder.
Speed: ~20× real time for 608×1080 at 25fps.
