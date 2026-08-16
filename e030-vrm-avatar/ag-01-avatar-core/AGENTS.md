# ag-01 — Avatar Core (server + client-A)

Build the `avatar-server` and the primary three.js/three-vrm client, plus the
capture helper for frame verification.

## Scope

1. **avatar-server** (Node, no framework needed): HTTP + WebSocket on
   **127.0.0.1:8787**. Serves:
   - `/` → viewer pages (client-A, and later client-B), static assets
   - `/models/<file>` → VRM files from `../models/`
   - `/media/<file>` → speech audio + `*.mouth.json`
   - WS `/` and `POST /cmd` → command queue (payload per experiment AGENTS.md)
   - Client identification: a client connects WS and registers an id; commands
     can target `"client":"all"` (default) or a specific id. Keep it simple —
     a broadcast is fine for v1.
2. **client-A** (`viewer.html`): three.js + `@pixiv/three-vrm`. Features:
   - load a VRM from `/models/…` served by the server
   - idle behavior: blink + breathing, look-at wander
   - implement the full command surface from the experiment AGENTS.md
   - `speak`: play audio + apply energy timeline to the mouth expression
   - `inspect`: report bones, expression names/weights, spring bones, version
   - background, lighting, camera facing the character (vertical 608x1080)
3. **capture helper** (`bin/capture-frame.sh`): screenshot the running Chrome
   tab via CDP (`Page.captureScreenshot`) into an output path. Document
   discovery of the target (remote-debugging-port) per e000 fundamentals.
4. **Model A**: download the sample VRM (URL in experiment AGENTS.md) once into
   `../models/`, validate GLB magic + size.
5. **Deps**: `npm i three @pixiv/three-vrm` (+ a static/serving approach of
   your choice — plain Node http server is enough; avoid heavyweight bundlers
   unless they make your life easier). Check the docs from the three-vrm.dev
   homepage for the correct `three` version to pair.

## Success criteria

- Client A loads Model A, shows idle blink/breathing, and responds to every
  command from the protocol table with correct JSON.
- `inspect` output is complete and truthful (verify against the actual model,
  don't hardcode counts).
- Frames captured at 2-3 poses/expressions render the character visibly
  (vision check yourself if possible; at minimum validate non-blank + size).

## Self-command
All blocking work runs in background; self-wake with context:
`tmux send-keys -t 30-1 "Self-wake: <pid> <step> <what to check> <next action>" Enter`
Always end with Enter. Deliver `done.txt` + `notify.sh done` when finished.

## Model
`opencode-go/deepseek-v4-flash`

## Command execution
- Background all servers/dev loops: `node server.js >/dev/null 2>&1 &`, self-wake.
- `timeout` every foreground command; never bare `sleep`/`kill`.
- Verify state, don't assume: `curl -s localhost:8787/health`, `ss -tlnp | grep 8787`.
- Kill by PID (`kill $PID`), never pkill.

## Pitfalls
- three-vrm API changes between versions — read its docs, don't guess API names.
- WebGL in headless Chrome: add `--enable-unsafe-swiftshader` (and
  `--use-angle=swiftshader`) or the page renders black. Verify before blaming code.
- The 11 MB model download once; keep a local copy.
- Run the page over http://127.0.0.1:8787 (file:// breaks fetch/WS).
- As a background agent it cannot see the page: verify via `/cmd inspect` +
  screenshots, never by "looking".

## Output
- `bin/avatar-server` (executable entry), `viewer.html`, `package.json`
- `output/` screenshots + `output/server-contract.md` (the de-facto protocol doc,
  update the experiment AGENTS.md table if it drifts)

## Inherits
- [../../../e000-fundamentals/AGENTS.md](../../../e000-fundamentals/AGENTS.md)
- [../AGENTS.md](../AGENTS.md)