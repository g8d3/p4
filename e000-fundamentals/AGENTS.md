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
- **Provider 1**: opencode-go — subscription via [opencode.ai](https://opencode.ai) (DeepSeek, Mimo, GLM, etc.).
- **Provider 2**: Xiaomi Token Plan — subscription via Xiaomi Mimo platform (`xiaomi/` prefix).
- **Provider 3**: Z.AI Coding Plan — subscription via Z.AI (`zai-coding-plan/` prefix).
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
| `XIAOMI_API_KEY` | API key for Xiaomi Token Plan (Singapore) |
| `XIAOMI_BASE_URL` | Base URL for Xiaomi Token Plan |

## Agent principles

- **Quality over speed**: don't just finish fast. Explore freely but balance it — don't add unnecessary code. Prioritize simple, well-made solutions.
- **Don't assume, verify**: before changing something, read the current state. Then think how to change it, act, and finally verify the result is as expected. Never assume something works without confirming.
- **Use your working directory**: don't use `/tmp` or external directories. Work inside your own directory and keep it organized however you see fit.
- **Command timeouts**: every command must have an estimated timeout. If unsure how long it will take, add a generous margin. Never leave a command without a timeout.
- **Never use pkill without extreme precision**: `pkill -f godot4` kills Godot processes across ALL tmux windows, including other agents. Use `kill $PID` with a specific process ID instead. If you must use pkill, scope it tightly (e.g., `pkill -f "Xvfb :99"`).
- **Blocking commands to background + self-wake (MANDATORY for all agents)**: every command must run in background with `>/dev/null 2>&1 &`. After each command, schedule a self-wake with `tmux send-keys -t <window> "check status" Enter`. **The `Enter` at the end is REQUIRED** — without it the message sits unsubmitted and the agent never receives it. Agents must NEVER run commands synchronously or block waiting for output.
- **When I (opencode) create agents, their AGENTS.md MUST include a `## Self-command` section** with the self-wake pattern. This is my responsibility as the agent creator.
- **sudo in a separate window**: OpenCode blocks `sudo` commands with a permission prompt. Agents must NOT give up when sudo is needed. Instead, open a new tmux window and run the sudo command there:
   1. `tmux new-window -n <sudo_name> -d`
   2. `tmux send-keys -t <sudo_name> "sudo <command>" Enter`
   3. The sudo prompt appears in a raw terminal, not blocked by OpenCode
   4. The agent can check completion with a self-wake after a reasonable delay
   5. **Clean up**: when the sudo window is no longer needed, close it: `tmux kill-window -t <sudo_name>`. Agents must not leave temporary windows behind.
- **Agents must clean up after themselves**: each agent is responsible for closing any tmux windows it creates (sudo windows, test windows, etc.) once they are no longer needed. Before finishing, an agent should verify its windows are cleaned up. Leaving orphan windows clutters the workspace for the user and other agents.

## Tmux window naming convention

All agent and sudo windows must follow this standard:

| Window | Pattern | Examples |
|--------|---------|----------|
| Root orchestrator agent | `a0` | `a0` |
| Experiment agent | `{exp}-{agent}` | `5-1`, `5-2`, `4-1` |
| Sudo window | `{exp}s` | `5s`, `4s` |

For example, in experiment e005:
- Agent ag-01 → tmux window `5-1`
- Agent ag-02 → tmux window `5-2`
- Sudo window for e005 → tmux window `5s`

This makes it easy to identify which experiment and agent a window belongs to, especially when running multiple experiments in parallel.

## Writing AGENTS.md: declarative over imperative

A common mistake is writing AGENTS.md like a recipe — "do step 1, then sleep 3, then do step 2". This makes agents robotic and blind to errors. If something goes wrong, they follow the recipe anyway because the instructions don't ask them to check.

Instead, write **declarative** instructions: describe the goal, the constraints, the tools, and common pitfalls. Let the agent figure out the steps.

| Imperative (bad) | Declarative (good) |
|---|---|
| `wf-recorder --geometry "0,0 608x1080"` | "Record the screen at 608×1080 vertical. Verify the output resolution with ffprobe." |
| `sleep 3` | "Wait until the browser is ready — check with pgrep or swaymsg." |
| "Step 1: X. Step 2: Y. Step 3: Z." | "Here's what success looks like. Here are the tools. Go explore and iterate." |
| No error checking | "If the video is < 1 MB, diagnose and retry before proceeding." |

**Key principles:**

1. **Define success criteria**, not steps. Tell the agent what "done" looks like (file size, resolution, visible content).
2. **List common pitfalls**. The agent will encounter them — help it recognize and fix them.
3. **Tell the agent to verify**. After any operation, check the result. `stat`, `ffprobe`, `swaymsg`, frame extraction — use them.
4. **Encourage iteration**. If the first attempt fails, the agent should diagnose, fix, and retry — not proceed with a broken result.
5. **Describe tools, not commands**. "Use swaymsg to inspect windows" is better than "run `swaymsg -t get_tree | python3 -c ...`". The agent can figure out the exact syntax.

The agent's model (Mimo 2.5, DeepSeek) is capable of reasoning, debugging, and adapting. The AGENTS.md should **enable** that capability, not override it with rigid instructions.

## Video recording

- **Verify output**: check that the video is not black, has audio, and narration matches what is on screen.
- **Continuous improvement loop, never stop**: The agent's job is not to produce one video and stop. It's a cycle:
  1. Produce a video
  2. Review the output (quality, errors, missing pieces)
  3. Review the process (what took long, what failed, what to optimize)
  4. Update your own AGENTS.md with the learnings
  5. Produce the next video with the improved process
  6. Repeat indefinitely
  - Each iteration makes the next one better. The agent gets faster, produces higher quality, and documents its own evolution. Stopping after one video is leaving value on the table.
- **Review the process, not just the product**: After finishing a video, the agent must reflect on its own process:
  - What steps took the most time? How much was thinking vs executing vs waiting?
  - What went wrong? What was surprising? What was harder/easier than expected?
  - What would you do differently next time?
  - Update your own `AGENTS.md` with the learnings so future runs improve.
  - This self-improvement loop is what makes each iteration better than the last. An agent that doesn't learn from its process will make the same mistakes forever.
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
- **Agent must be reactive, not scripted**: The agent is equivalent to a human teacher. It must interact with the system in real-time, observe, think, and react — NOT pre-write a script, execute it robotically, and narrate over a recording. A scripted recording where the agent just runs commands and then narrates after is unacceptable. The agent must think as it goes, explain its reasoning in the moment, and respond to what it sees on screen.
- **Narration must match the screen**: What the narrator says must be synchronized with what is shown. If displaying system resources, explain WHY — what you're looking for, what the numbers mean, what conclusion you draw. Showing a dashboard without context is noise.
- **Human pacing**: Agents operate at machine speed. Videos must be paced for human consumption — allow time to read text, process information, follow the reasoning. Do not flash information faster than a human can read.
- **Video structure**: Every video needs a clear arc — introduction (what you'll do and why), body (the work), conclusion (what you found, call to action or cliffhanger). A video without structure is confusing.
- **Resource metadata**: Every video output MUST include a `metadata.json` file in `./output/` listing ALL resources used:
  - **Hardware**: CPU model/usage, GPU model/usage, RAM, display type (Wayland headless, resolution)
  - **Software**: OS, window manager, capture tool (wf-recorder/ffmpeg), encoding (h264_vaapi), subtitles tool
  - **Cloud**: providers used, models used, token count, cost, latency
  - **Narration**: voice model, TTS engine, language
  - **Timestamps**: recording start/end, duration
  - This enables tracing errors, comparing efficiency, and reproducing results.
- **Video types** (deprecated — only exploratory is valid):
  - ~~**Scripted**: agent follows a predefined script and narrates it as written.~~ Do not use.
  - **Exploratory (only valid type)**: agent narrates live what it is doing — what it plans, problems it finds, how it solves them, its decisions in the moment. No script, reactive. This is the only acceptable format.

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

By default agents use DeepSeek V4 Flash. To use a different model or provider, specify it when launching:

```
opencode -m opencode-go/mimo-v2.5         # opencode-go provider
opencode -m xiaomi/mimo-v2.5              # Xiaomi Token Plan provider
opencode -m zai-coding-plan/glm-5.1       # Z.AI Coding Plan provider
```

The agent's AGENTS.md should declare its required model in a `## Model` section. The orchestrator reads this and uses the corresponding `-m` flag.

### Provider vs model distinction

**Providers** have their own compute/subscription resources. **Models** run on providers. A single provider (e.g. opencode-go) can host many models.

| Provider | Provider ID prefix | Subscription | Typical models |
|----------|-------------------|-------------|----------------|
| OpenCode Go | `opencode-go/` | Monthly subscription | deepseek-v4-flash, mimo-v2.5, glm-5.1, kimi-k2.6, minimax-m2.7 |
| Xiaomi Token Plan (Singapore) | `xiaomi-token-plan-sgp/` | Token-based plan | mimo-v2.5, mimo-v2-tts, mimo-v2-omni |
| Xiaomi Token Plan (Europe) | `xiaomi-token-plan-ams/` | Token-based plan | mimo-v2.5, mimo-v2-tts, mimo-v2-omni |
| Xiaomi Token Plan (China) | `xiaomi-token-plan-cn/` | Token-based plan | mimo-v2.5, mimo-v2-tts, mimo-v2-omni |
| Z.AI Coding Plan | `zai-coding-plan/` | Coding plan Pro (5h rolling window) | glm-4.7, glm-5.1, glm-5-turbo |
| OpenCode Zen | `opencode/` | Pay-per-use | All tested models |

Note: Xiaomi Token Plan has 3 regional variants. Use `xiaomi-token-plan-sgp/` (Singapore) — lowest latency from our location.

### Using multiple providers in parallel

When running multiple agents simultaneously, use different providers to maximize token throughput (each provider has independent compute):

```
# ag-01 with opencode-go
opencode -m opencode-go/mimo-v2.5

# ag-02 with Xiaomi Token Plan
opencode -m xiaomi/mimo-v2.5

# ag-03 with Z.AI Coding Plan
opencode -m zai-coding-plan/glm-5.1
```

### Listing available models

```bash
opencode providers              # list configured providers and credentials
opencode models                 # list all available models across all providers
opencode models opencode-go     # list models for a specific provider
```

Vision-capable models (for self-reviewing videos): `opencode-go/mimo-v2.5`, `xiaomi-token-plan-sgp/mimo-v2.5`, `zai-coding-plan/glm-4.7` (has vision).

### Model cost awareness

Z.AI Coding Plan has a **5-hour rolling credit window**. Higher-tier models (glm-5.1) deplete credits faster:
- Prefer `zai-coding-plan/glm-4.7` for daily production — balances cost and capability
- Reserve `zai-coding-plan/glm-5.1` for final polish or complex tasks
- Track token consumption per session to understand burn rate

This applies to all providers: **consistency over peak quality**. Produce videos even if imperfect, using cheaper models. Iterate on quality with selective use of expensive models.

### Security: API keys and secrets

NEVER hardcode API keys, tokens, or secrets in AGENTS.md or any file that could be committed to git:

```bash
# WRONG — in AGENTS.md:
XIAOMI_API_KEY=tp-xxx   # NEVER DO THIS

# RIGHT — reference env vars only:
export XIAOMI_API_KEY=tp-xxx   # in ~/.zshrc, never in repo
```

Before launching agents, always source the shell config to make env vars available:
```bash
. ~/.zshrc; cd <agent_dir> && opencode -m <provider/model>
```

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

### OpenCode synchronous command trap

**Problem**: OpenCode runs commands synchronously — the agent blocks until the command finishes. A human would notice a command is taking too long and proactively kill it, but the agent can't. This means:

- `sleep 300` blocks the agent for 5 minutes doing nothing
- `kill $PID` of a zombie/stuck process hangs forever
- Any command that doesn't exit becomes a deadlock

**Solutions** (in order of preference):

1. **`timeout`**: Always wrap commands that might hang:
   ```bash
   timeout 5 kill $PID 2>/dev/null   # instead of plain kill
   timeout 10 ffmpeg ...              # ffmpeg with hard cap
   ```

2. **Background + self-wake**: Put the command in background and check with self-wake:
   ```bash
   ffmpeg ... &
   CMD_PID=$!
   (sleep 5; tmux send-keys -t 5-3 "Self-wake: check CMD_PID=$CMD_PID, if still running after 5s, kill it." Enter) &
   ```

3. **Check first**: Before running a blocking command, check if it's necessary:
   ```bash
   pgrep ffmpeg && echo "already running, skipping" || ffmpeg ...
   ```

**Rule of thumb**: If a command takes more than 2 seconds, it needs `timeout` or background + self-wake. Never run bare `kill`, `sleep`, or long-running commands synchronously.

### Orchestrator workflow: fix agents without restart (MANDATORY FIRST STEP)

**When an agent is stuck, wrong, or confused: ALWAYS send a corrective message first. NEVER kill and relaunch as first action.**

```
FIRST: send a targeted message to fix the issue
  tmux send-keys -t <window> "Leé tu AGENTS.md / Hacé X / Corregí Y" Enter

ONLY IF the agent doesn't recover after 60 seconds:
  THEN consider killing and relaunching
```

**Why**: Killing and relaunching wastes all the agent's work, context, and tokens. A simple message often fixes the problem in seconds.

**Common corrective messages:**
- Agent didn't read its AGENTS.md: `"Leé tu AGENTS.md: /path/to/AGENTS.md"`
- Agent is over-thinking: `"Dejá de planificar. Ejecutá un comando ahora."`
- Agent went off track: `"Tu tarea es X, no Y. Enfocáte en X."`
- Agent is stuck on a command: `"Si ese comando falló, probá alternativa Z."`

**Live message pattern** (for edits to AGENTS.md):
```
1. Orchestrator edits agent's AGENTS.md (persistent for future runs)
2. Orchestrator sends the delta as a live message
   tmux send-keys -t <window> "Apply this change: <specific instructions>" Enter
3. Agent continues from current state, applying only the diff
```

**Pros**: No work lost, no full re-read, fast iteration.
**Cons**: Agent's conversation history still has old instructions. If the change is fundamental, a restart may be cleaner.

**Rule of thumb**: For small deltas (tool flags, pipeline steps, content ideas), use live message. For complete rewrites or when stuck for >2 minutes after corrective messages, restart.

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

## Commits

- **Commit frequently** — after each meaningful change, commit. This applies to both agents working in their directories and the orchestrator.
- **Commit message format**: `<experiment>: <description of change>`
- **Scope**: commit all files in the working directory. The orchestrator commits at the project root.
- **No secrets**: never commit API keys, tokens, or passwords.

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

## Screen recording (Wayland headless)

For screen recording with a virtual display, use the shared `record.sh` script:

```bash
../bin/record.sh <name> <duration_sec>
```

This handles: sway headless startup (Vulkan renderer), foot terminal, wf-recorder capture with tested flags, VAAPI re-encode, and metadata output.

**Tested flags for wf-recorder with Sway headless:**
- `--no-dmabuf` — required, DMA-BUF produces black frames
- `--no-damage` — required, headless backend doesn't emit damage events
- `-c libx264` — use CPU encoding during capture (VAAPI in wf-recorder produces corrupt files from headless)
- Re-encode with `ffmpeg -vaapi_device /dev/dri/renderD128 -vf "format=nv12,hwupload" -c:v h264_vaapi` afterward

**Sway config for headless:**
```
xwayland disable
output * resolution 608x1080
output * bg #0d1117 solid_color
default_border none
exec_always true
```

**Multiple virtual displays on one sway**: sway supports multiple headless outputs via `swaymsg create_output`. Each gets a name like `HEADLESS-1`, `HEADLESS-2`, etc. Record a specific output with `wf-recorder -o HEADLESS-1`. Multiple recordings on different outputs run simultaneously without conflict.

**Sway is persistent**: start sway once on boot/first use. Do NOT kill it between recordings. Use `swaymsg` to create/list/delete outputs as needed.

If sway needs to be started:
```bash
WLR_BACKENDS=headless WLR_RENDERER=vulkan WLR_LIBINPUT_NO_DEVICES=1 sway --config sway-headless.conf &
```
