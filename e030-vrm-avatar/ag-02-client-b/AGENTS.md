# ag-02 — Client B + avatar CLI

Build a **second three.js/three-vrm renderer client** (client-B) and the
**`avatar` CLI**. Runs in tmux window `a1` (Command Code agent).

## Scope

1. **client-B**: an independent three.js/three-vrm page that implements the
   SAME WS control protocol as client-A (command table in `../AGENTS.md`). You
   may differ from client-A in build tooling (esbuild vs Vite vs none), scene
   extras (VRMA animation support, shadows, background, camera), and code
   structure — but the JSON command/response contract MUST match exactly so the
   `avatar` CLI and later the video pipeline work against either client.
2. **Model B**: find and verify a SECOND distinct VRM character (not the
   sample used by ag-01). Validate the download (GLB glTF magic, size) and
   document its license/source. If no stable second source exists, reuse the
   sample model and distinguish the client by implementation.
   Candidate sources to verify (do not trust blindly — check magic + size):
   three-vrm docs sample links, vrm.dev, VRoid Hub sample URLs mentioned in
   the three-vrm community/discussions.
3. **`avatar` CLI** (`bin/avatar`): thin wrapper over the server. Subcommands:
   - `avatar load <model>` · `expression <name> [weight]` · `lookAt <x> <y>`
   - `bone <name> <rx> <ry> <rz>` · `speak <audio> [mouth.json]`
   - `inspect` · `snapshot <out.png>` · `script <script.json>` (replay a
     performance script with timing; `speak` blocks for its own duration)
   - `--client <id>` to target client-B explicitly (protocol supports it)
   Each subcommand POSTs JSON to the server `/cmd`. `script` reads a
   performance script: `[{ "t_ms": 0, "cmd": {…} }, …]` — later used by ag-03.
4. **Deps**: Node project (`npm i three @pixiv/three-vrm`). Pair the three-vrm
   version with the correct `three` (read three-vrm.dev docs).

## Success criteria

- Client-B loads Model B, runs idle behavior, and answers every protocol
  command correctly (test through the shared server, target it explicitly).
- `avatar inspect --client B` returns truthful model info (verify, don't
  hardcode).
- Screenshots at 2-3 poses/expressions show the character visibly (non-blank,
  review yourself with the vision model if available).
- `avatar script demo.json` replays a short sequence (pose → expression →
  smile → speak) without manual intervention; document the DM output.

## Self-command
Background every blocking command; self-wake always:
`tmux send-keys -t a1 "Self-wake: <pid> <step> <what to check> <next>" Enter`
Send production commands from this window; the server/client run elsewhere —
verify via curl/`inspect` + screenshots, not visually.

## Model
Command Code — current model in this window (`cmd`); this agent runs inside
the existing a1 session.

## Command execution
- `cmd` agent: you are not under opencode, but the same rules apply: timeout
  every command, background servers, kill by PID.
- Verify server reachable (`curl -s localhost:8787/health`) before control tests.

## Pitfalls
- The protocol is shared: never invent commands or change shapes without
  updating `../ag-01-avatar-core/output/server-contract.md`.
- Headless WebGL needs `--enable-unsafe-swiftshader`/`--use-angle=swiftshader`;
  black frames means flags, not code.
- Download Model B once; never re-fetch in loops.
- Do not overwrite ag-01's `models/model-a.vrm`; use `models/model-b.vrm`.

## Output
- `bin/avatar` (executable), `viewer-b.html`, `package.json`
- `../models/model-b.vrm` (verified) + `output/model-b-source.md`
- `output/demo-script.json` + demo screenshots
- `done.txt` + `notify.sh done "ag-02 client-B + avatar CLI:…"`

## Inherits
- [../../../e000-fundamentals/AGENTS.md](../../../e000-fundamentals/AGENTS.md)
- [../AGENTS.md](../AGENTS.md)