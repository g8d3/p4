# e030 — VRM Avatar

Create a **programmatically controllable VRM avatar** rendered with
**three.js + `@pixiv/three-vrm`**. Two interchangeable renderer clients (two
characters/implementations, built in parallel by two agents), one shared
control protocol, and a video production pipeline — producing both an
interactive viewer and talking-avatar videos.

## Deliverables

1. **Viewer + control API**: three.js/`@pixiv/three-vrm` pages that load a VRM
   model, plus a local HTTP+WebSocket control server that drives them. Any
   script or agent can pose the avatar, change expressions, set look-at
   targets, play animations, and trigger speech with lip sync.
2. **Two renderer clients, one protocol**: two independent three.js/three-vrm
   clients (built in parallel), interoperable behind the same WS control
   protocol, each able to show a different character.
3. **Preview/verification**: deterministic frame captures (headless WebGL) so
   renders can be reviewed by a vision-capable model.
4. **Talking-avatar video**: an avatar performs a narration (KIE TTS), is
   captured at 608x1080, and encoded to a GPU (VAAPI) final video with
   `metadata.json`.

## Architecture

```
avatar-server (Node, HTTP+WS on 127.0.0.1:8787)
   │  WS control protocol (shared, versioned)
   ├──▶ client-A (three-vrm viewer.html  → ag-01)   [avatar A]
   ├──▶ client-B (three-vrm viewer-B    → ag-02)   [avatar B]
   ▼
capture: (A) headless Chrome CDP screenshot  → stills for verification
          (B) sway headless + wf-recorder      → real-time footage for video (ag-03)
```

- **avatar-server** (ag-01): single Node process, HTTP+WS on **8787**. Serves
  the viewer pages and VRM files; forwards commands; serves speech audio +
  lip-sync timeline.
- **client-A** (ag-01): primary `viewer.html` page (three.js + three-vrm),
  idle behavior (blink, breathing), WS command executor, diagnostics.
- **client-B** (ag-02): second three.js/three-vrm client. May differ in build
  tooling (esbuild vs Vite), extras (VRMA animation, shadow, background), and
  MUST load a **second character** (another VRM). Same WS protocol, same JSON
  command/response shapes.
- **`avatar` CLI** (ag-02): thin wrapper over the server so humans and agents
  control either client from the shell.

### Control command surface (shared protocol)

Commands travel as JSON over the WebSocket (and `POST /cmd`). Clients MUST
implement exactly these; responses mirror the command with `"ok":true` plus
result fields:

| Command | Example payload | Effect |
|---|---|---|
| `load` | `{"model":"models/model-a.vrm"}` | Load a VRM file served by the server |
| `expression` | `{"name":"happy","weight":1}` | Set a VRM expression weight |
| `resetExpression` | `{}` | Clear all expressions |
| `lookAt` | `{"x":0.4,"y":0.2}` | Set look-at target (normalized) |
| `bone` | `{"name":"leftUpperArm","rotate":[0,0.5,0]}` | Direct humanoid bone control |
| `animation` | `{"url":"…","loop":true}` | Play a VRMA/glb animation |
| `speak` | `{"audio":"media/narration.mp3","mouth":"media/narration.mouth.json"}` | Play audio + drive mouth-open expression from energy timeline |
| `setIdle` | `{"on":true}` | Enable/disable idle blink+breathing |
| `inspect` | `{}` | Return model state: bones, expressions, spring bones, renderer info |

### Lip sync

Speech audio → per-window RMS energy → `mouth.json` timeline `[[t_ms, weight],…]`.
The client maps weight to the mouth/`aa` expression. Energy extraction uses
ffmpeg (decode to mono PCM, ~80-100 ms windows). See e000 fundamentals for TTS
and transcription steps.

### Video production (ag-03, reused p4 pipeline)

1. Narration: `e019-kie-image-api/ag-01/bin/kie-tts.sh` (approved voice).
2. Transcribe: `e018-hyprframes-browser-video/ag-02/bin/transcribe.sh` → word timestamps.
3. Build a **performance script** (expression cues + `speak` at synced times)
   → `output/performance.json`.
4. Play the performance while capturing: sway headless 608x1080 + wf-recorder
   (`--no-dmabuf --no-damage -c libx264`).
5. Re-encode to `h264_vaapi` with `e023-build-in-public/bin/encode_vaapi.sh`.
   **Final video MUST be VAAPI** (verify `stream_tags=encoder`).
6. Write `metadata.json` (e000 fundamentals).

## Tools and sources

- **Library**: `three` + `@pixiv/three-vrm` (npm registry verified reachable).
  Verify the compatible version pair from the three-vrm docs before coding.
- **Model A** (verified GLB 10.7 MB, glTF2):
  `https://raw.githubusercontent.com/pixiv/three-vrm/dev/packages/three-vrm/examples/models/VRM1_Constraint_Twist_Sample.vrm` — download ONCE into `models/`, never re-fetch.
- **Model B** (ag-02): find and verify a second, distinct VRM character (size +
  glTF magic check; document license). Prefer official vrm.dev / three-vrm /
  VRoid Hub sample URLs. If no stable second source exists, reuse Model A and
  make client-B distinguished by implementation.
- **Renderer hosts**: `google-chrome` (installed). Headless WebGL needs flags:
  Chrome ≥137 requires `--enable-unsafe-swiftshader` (`--use-angle=swiftshader`
  for software WebGL). GPU real-time footage uses sway headless + wf-recorder
  (sway is currently NOT running — start per e000 if needed).
- **Vision review**: `zai-coding-plan/glm-4.7` or `opencode-go/mimo-v2.5`.

## Parallel agents (one per provider)

| Agent | Provider / model | tmux | Scope |
|---|---|---|---|
| ag-01 | `opencode-go/deepseek-v4-flash` | `30-1` | avatar-server + client-A (+ model A) |
| ag-02 | `cmd` (Command Code, existing window) | `a1` | client-B + `avatar` CLI (+ model B) |
| ag-03 | `zai-coding-plan/glm-4.7` | `30-3` | video production (performance → capture → encode) |

All three speak the same protocol and consume/produce files in their own
`output/`. ag-03 may start TTS/transcribe/pipeline work before clients exist;
clients must be ready with a minimal `inspect` + `expression` before production.

## Pitfalls

- three-vrm load is async — wait for renderer init and verify `vrm.humanoid`
  before issuing control commands.
- Verify every screenshot is non-blank with the character visible (vision
  review + file-size sanity).
- Keep model files local in `models/`; never hang a session on re-download.
- Final video encode MUST be VAAPI; verify with ffprobe `stream_tags=encoder`.
- All background services via background + self-wake; never block
  synchronously. Clean up tmux windows created (`30-1`, `30-3`).
- Remote CDP discovery: `ss -tln | grep 9222`.

## Directory layout

```
e030-vrm-avatar/
├── AGENTS.md
├── models/               # VRM files (ag-01 owns)
├── ag-01-avatar-core/    # server + client-A + capture helper → tmux 30-1
├── ag-02-client-b/       # client-B + avatar CLI + model B     → tmux a1
├── ag-03-video/          # talking-avatar video pipeline       → tmux 30-3
└── ag-0N/output/         # each agent's deliverables (AgentFS)
```

## Success criteria

- `avatar inspect` works against both clients; both report humanoid bones,
  expressions, renderer info.
- Frames at several poses/expressions render correctly from both clients
  (vision model confirms; no black frames).
- A 30-60 s talking-avatar video: 608x1080, audible narration, mouth moves
  with speech, VAAPI tag verified, `metadata.json` present.
- Programmatic control demonstrable with one replayable script (poses +
  expressions + speech), no manual interaction.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command/timeout rules, video pipeline, GPU encoding, sway/wf-recorder, browser/CDP
- [../AGENTS.md](../AGENTS.md) — p4 experiment index and context