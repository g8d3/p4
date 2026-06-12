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
- **Models**: DeepSeek V4 Flash, MiniMax 2.5 (non-Pro). MiniMax 2.5 supports vision/multimodal, ideal for video tasks.
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
   tmux send-keys -t <name> "Read AGENTS.md and execute the task" Enter
   ```

**Important**: `opencode "text"` is NOT interactive — it treats the argument as a directory. Always launch opencode with no arguments, then send the prompt after it loads.

The agent's AGENTS.md is its sole context. Do not pass task details in the prompt — the agent reads them from the file. This tests that the directory + AGENTS.md contract is sufficient.

## Language

- User dictates in Spanish.
- All files, code, and agent responses are written in English.
