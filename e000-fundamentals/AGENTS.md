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

Each AGENTS.md declares what it needs from parent levels in an `## Inherits` section:

```markdown
## Inherits
- `../../e000-fundamentals/AGENTS.md` — principles, no /tmp, timeouts
- `../AGENTS.md` — experiment scope
```

The launch prompt must tell the agent to read inherited files:

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
