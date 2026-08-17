# ag-01 — Avatar Studio (create + control on one page)

Build the entire studio: a minimal Node server + one mobile-friendly web page
where the user both **creates** and **controls** a VRM avatar.

## Deliverable

One page, one server. Everything else is out of scope for v1.

**Server** (`server.js`, Node, no framework): serves on **0.0.0.0:8787**
- `/` → the studio page
- `/models/<name>.vrm` → VRM files from `./models/`
- That's it. No API routes, no WebSocket, no CLI.

**Page** (`index.html`, three.js + `@pixiv/three-vrm`):
- **Create panel**: character gallery — list available models (scan a
  `models/` manifest), click one to load it into the canvas. Include a
  "capture snapshot" button that produces a PNG the user can download
  (a pose/expression gallery).
- **Control panel** (same page): camera drag-to-rotate, expression
  buttons/sliders (happy, sad, angry, surprised, blink…), a look-at target
  control, idle blink/breathing toggle. Touch-friendly.
- **Mobile-first**: vertical layout, readable on a phone, gestures for rotate.
- Shows model info: name, bone count, expression list.

**Models** (`models/`): 2+ verified VRM files (glTF magic + size). Source them
from the three-vrm official samples / vrm.dev samples; document license +
source. Store locally once.

## Success criteria

- Open the page from a phone on the LAN (`http://<lan-ip>:8787/`): character
  visibly renders (NOT black), you can switch characters, rotate, change ≥3
  expressions, and download a snapshot.
- Server reachable from LAN (`ss` shows 0.0.0.0:8787; `ufw` inactive).
- Without a client connected, the server stays up and the page still works
  when you open it later.
- `output/`: screenshots of ≥2 characters in different expressions +
  `output/models.md` (sources, licenses, verification hashes).

## Self-command
Background all blocking work; self-wake with context:
`tmux send-keys -t 30-1 "Self-wake: <pid> <step> <what to check> <next>" Enter`
Always end with Enter. Write `done.txt` + `notify.sh done` when finished.

## Window discipline
- Your window is **30-1**. Never `send-keys`/`kill-window`/`rename-window`/
  `new-window` on any other window (`a0`, `a1` are others). Never pkill.
  Kill only your own PIDs.
- The orchestrator (a0) talks to you; you never message other agents.

## Model
`opencode-go/deepseek-v4-flash`

## Command execution
- `timeout` every foreground command; background the server
  (`node server.js >/dev/null 2>&1 &` + self-wake); never bare `sleep`/`kill`.
- Verify with facts: `curl -s localhost:8787/` http host, `ss -tlnp | grep 8787`,
  screenshot → non-blank + size. Don't trust "it works" without a screenshot.

## Pitfalls
- Headless WebGL verification: Chrome ≥137 needs `--enable-unsafe-swiftshader`
  (`--use-angle=swiftshader`), else everything renders black. On the REAL phone
  no flags are needed.
- three+three-vrm API changes between majors: read the three-vrm docs for the
  correct `three` version before coding. Loading is async — await renderer +
  `vrm.humanoid` before showing controls.
- Keep scope tight. If you start writing a CLI or a video encoder, STOP —
  that's out of v1.
- Models are ~11 MB: fetch once, keep local, never re-download in loops.

## Output
`server.js`, `index.html`, `models/`, `output/screenshots/*.png`,
`output/models.md`, `done.txt` + `notify.sh done`.

## Inherits
- [../../../e000-fundamentals/AGENTS.md](../../../e000-fundamentals/AGENTS.md)
- [../AGENTS.md](../AGENTS.md)