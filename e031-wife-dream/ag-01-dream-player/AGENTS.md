# ag-01 — Dream Player (paper-cutout 3D narrative)

Build the entire e031 deliverable: a minimal Node server + one mobile-friendly
self-contained web page implementing the spec in `../plan.md`.

## Deliverable

One page, one server. Everything else is out of scope for v1.

**Server** (`server.js`, Node, no framework): serves on **0.0.0.0:8788**
- `/` → the player page
- `/lib/*` → local lib files if ever needed (CDN is primary)
- No API routes, no WebSocket, no CLI.

**Page** (`index.html`, self-contained: CSS + JS inline, Three.js + OrbitControls
+ GSAP from CDN):
- **Paper-cutout 3D scene**: layered `THREE.PlaneGeometry` cutouts with canvas
  textures placed along Z for parallax; soft directional light + shadows on a
  paper-textured background.
- **9-act storyboard** exactly as in `plan.md` §4 — each scene has its own
  layered diorama + camera move (Ken Burns / dolly via GSAP or lerp). Character
  traits stay exact across scenes (protagonist: short dark hair + round
  clear-frame glasses; villain: older man, brown suit, mustache). Scene 9 =
  backwards pink fuzzy glitter high heels close-up.
- **Glassmorphism HUD** (bottom): play/pause, scrubber, volume, TTS provider
  selector, scene indicators, fullscreen. Cinzel/Playfair Display titles,
  Inter subtitles. Fluid units, focus states, mobile-first.
- **Audio engine** (modular): KIE Gemini TTS primary (Bearer `KIE_API_KEY`,
  async createTask → recordInfo → resultUrls), Deepgram `aura-2` alternative
  (`DEEPGRAM_API_KEY`), `window.speechSynthesis` fallback. On audio `ended`,
  auto-advance to next scene. Subtitles synced per scene.
- **Performance**: `requestAnimationFrame` with capped delta, `devicePixelRatio`
  capped at 2, cleanup/disposal on scene teardown.

## Success criteria

- Open the page from a phone on the LAN (`http://<lan-ip>:8788/`): 3D scene
  visibly renders (NOT black), scene 1 narration plays (or falls back cleanly
  to speechSynthesis when no API key), subtitles show, controls work, scenes
  advance.
- Server reachable from LAN (`ss` shows 0.0.0.0:8788).
- `output/`: screenshots of ≥2 scenes + the HUD.

## Self-command
Background all blocking work; self-wake with context:
`tmux send-keys -t 31-1 "Self-wake: <pid> <step> <what to check> <next>" Enter`
Always end with Enter. Write `done.txt` + `notify.sh done` when finished.

## Window discipline
- Your window is **31-1**. Never `send-keys`/`kill-window`/`rename-window`/
  `new-window` on any other window. Never pkill. Kill only your own PIDs.
- The orchestrator (a0) talks to you; you never message other agents.

## Model
`opencode-go/deepseek-v4-flash`

## Command execution
- `timeout` every foreground command; background the server
  (`node server.js >/dev/null 2>&1 &` + self-wake); never bare `sleep`/`kill`.
- Verify with facts: `curl -s localhost:8788/`, `ss -tlnp | grep 8788`,
  screenshot → non-blank + size. Don't trust "it works" without a screenshot.

## Pitfalls
- Headless WebGL verification: Chrome ≥137 needs `--enable-unsafe-swiftshader`
  (`--use-angle=swiftshader`), else everything renders black. On the REAL phone
  no flags are needed.
- Three.js API changes between majors: pin CDN versions known to work together.
- KIE TTS is async (taskId → poll recordInfo) and returns URLs that expire
  (~20 min) — fetch promptly, don't cache.
- Keep scope tight. If you start writing a CLI or a video encoder, STOP —
  that's out of v1.

## Output
`server.js`, `index.html`, `output/screenshots/*.png`, `done.txt` +
`notify.sh done`.

## Inherits
- [../../../e000-fundamentals/AGENTS.md](../../../e000-fundamentals/AGENTS.md)
- [../AGENTS.md](../AGENTS.md)
