# e027 Open Design — ag-01 exploration notes

Live session notes for the Open Design experiment. Date: 2026-08-15.
Author: ag-01 (opencode-go/deepseek-v4-flash).

## How to start (verified on this machine)

```sh
# repo location (gitignored, cloned depth 1)
/home/vuos/code/p4/e027-open-design/upstream  (commit 30fc648)

# Node 24 + pnpm pin via corepack
node --version          # v24.16.0
corepack enable
cd upstream
pnpm --version          # must print 10.33.2 (repo pins pnpm@10.33.2)

pnpm install            # ~1.5 min on warm cache (monorepo, heavy)
pnpm --filter @open-design/daemon build   # builds apps/daemon/dist/cli.js (the `od` binary)

# start daemon + web (background via tools-dev)
pnpm tools-dev start web --daemon-port 7457 --web-port 5173
```

Ports: daemon `127.0.0.1:7457`, web UI `127.0.0.1:5173` (dev server, next.js). In this
experiment we pinned these; the default picks random free ports.

## `od` name clash

`/usr/bin/od` is the GNU octal-dump tool. The Open Design `od` is
`upstream/apps/daemon/bin/od.mjs` (wraps `dist/cli.js`). Use:

```sh
export OD_BIN=/home/vuos/code/p4/e027-open-design/upstream/apps/daemon/bin/od.mjs
export OD_DAEMON_URL=http://127.0.0.1:7457
node $OD_BIN <subcommand> ...
```

Top-level `od` (no subcommand) STARTS the daemon/web — it is NOT a client.
There is no `od --version`; the version is served at `/api/health`.

## Agent-critical commands

```sh
# catalog
node $OD_BIN skills list                 # 162 functional skills
node $OD_BIN skill list                  # alias
node $OD_BIN skill show <id>             # JSON of one skill
node $OD_BIN plugin list                 # 460 bundled plugins
node $OD_BIN project list --json         # projects

# projects (headless runs)
node $OD_BIN project create --name "<t>" --skill <skillId> --design-system <dsId>
node $OD_BIN project create --name X --skill open-design-landing --design-system default

# media (image/video/audio) through the daemon
node $OD_BIN media generate --project <id> --surface video --model hyperframes-html \
  --output out.mp4 --composition-dir .hyperframes-cache/<id>
node $OD_BIN media wait <taskId> --since <n>

# MCP integration
node $OD_BIN mcp install opencode [--print|--json] [--uninstall]
node $OD_BIN mcp                       # run stdio MCP server
```

## The `od skill run` command does NOT exist (live delta)

Mission docs say `od skill run open-design-landing --output ...`. The live CLI has
NO such command. `od skill` supports only `install|list|show|uninstall`. Headless
skill execution is done differently (below). Report this delta.

## How a headless skill run actually works

The web UI drives runs via `POST /api/runs` (the daemon spawns a local agent CLI,
composes the system prompt from skill + DESIGN.md, streams SSE events). The CLI has
no direct "run" command, but the HTTP API is public:

```sh
curl -X POST http://127.0.0.1:7457/api/runs \
  -H 'Content-Type: application/json' -H 'X-OD-Client: cli' \
  -d '{"agentId":"opencode","projectId":"<id>","skillId":"open-design-landing",
       "designSystemId":"default","sessionMode":"design","message":"...", "model":null}'
# → {"runId": "..."}
curl -N http://127.0.0.1:7457/api/runs/<runId>/events   # SSE stream
```

- The spawned agent runs `opencode run --format json` as a child of the daemon,
  in the project workspace (`.od/projects/<id>/`).
- The skill is staged under `.od-skills/<skill>-<hash>/` inside the project.
- The prompt is the composed system prompt (base + DESIGN.md + skill body).
- Design systems are injected as text into the prompt; `tokens.css` is the
  machine-readable binding the agent pastes into artifacts.

### Which runtimes the daemon detects (this machine)

available: opencode, claude, byok-opencode, hermes, grok-build, antigravity,
reasonix, mimo. Not available (fine, optional): amr/vela (web UI warns), codex,
devin, kimi, qwen, cursor-agent, etc. `opencode` is the primary runtime here.

## open-design.json spec fields (in practice)

From `plugins/spec/examples/create-slides-pitch/open-design.json`:

```json
{
  "$schema": "https://open-design.ai/schemas/plugin.v1.json",
  "specVersion": "1.0.0",
  "name": "create-slides-pitch",
  "od": {
    "kind": "skill",            // registry classification: skill|scenario|atom|bundle
    "taskKind": "new-generation", // new-generation|code-migration|figma-migration|tune-collab
    "mode": "deck",             // prototype|deck|template|design-system|image|video|audio
    "scenario": "finance",      // gallery/filter hint
    "surface": "web",           // web|image|video|audio
    "preview": { "type": "html", "entry": "./example.html" },
    "useCase": { "query": { "en": "...", "zh-CN": "..." } },
    "context": { "skills": [...], "craft": [...], "assets": [...], "atoms": [...] },
    "pipeline": { "stages": [...] },
    "inputs": [ { "name": "company", "type": "string", "required": true } ],
    "capabilities": ["prompt:inject", "fs:write"]
  }
}
```

Note: older bundles carry `od.inputs`/`od.parameters`/`od.outputs`/
`od.capabilities_required`; the registry preserves them but the current protocol
documents them as not used to render forms. The `SKILL.md` frontmatter `od:`
fields (`mode`, `surface`, `scenario`, `craft.requires`, `design_system.requires`)
are what drive composition.

Seven registry modes (`docs/modes.md`): prototype, deck, template,
design-system, image, video, audio. These differ from the six New Project UI tabs.

## Skills vs design templates vs plugins (three catalogues)

| Catalogue | Dir | API | Count |
|---|---|---|---|
| Functional skills | `skills/` | `/api/skills` | 162 |
| Design templates (rendering) | `design-templates/` | `/api/design-templates` | 130+ |
| Plugins (bundled) | `plugins/_official` + registry | `/api/plugins` | 460 |

`open-design-landing` is a **design template**, not a functional skill — but
`/api/design-templates` lists it, and it can be used as a project `skillId`.

## Design systems (DESIGN.md)

- Bundled: `design-systems/<id>/DESIGN.md` + `tokens.css` + `manifest.json` etc.
- User-managed: `<OD_DATA_DIR>/design-systems/<id>/` — the daemon rescans per request
  (no restart needed). New DS needs `metadata.json` with `"status": "published"`
  or projects reject it with `DESIGN_SYSTEM_NOT_PUBLISHED`.
- `tokens.css` is the machine contract: a `:root` block with standard token names
  (`--bg --surface --fg --muted --border --accent --font-display ...`) that agents
  paste verbatim and reference via `var(--name)`.
- DESIGN.md has 9+ human headings (Visual Theme, Color Palette & Roles, Typography
  Rules, Component Stylings, Layout Principles, Depth & Elevation, Do's and Don'ts).

## Modes → output types

- web/landing/prototype → `index.html` (single-file)
- deck → `index.html` (in-page slide nav) + optional `slides.json`
- dashboard → `index.html`
- image/video/audio → media files via `od media generate`
- video via `hyperframes-html` → **HTML composition rendered to mp4 with Chrome**
  (no generative video model). Composition dir must contain `hyperframes.json`,
  `meta.json`, `index.html`. Render dispatches through the daemon:
  `od media generate --surface video --model hyperframes-html --composition-dir ...`

## Headless vs web-UI requirements

- **Headless (CLI/API)**: project create + POST /api/runs + SSE. Works fully.
  Skills that are pure-function composers (open-design-landing) run deterministically.
- **Web UI**: needed for the interactive onboarding gate (AMR/Vela cloud sign-in
  wall) unless `app-config.json` has `onboardingCompleted: true`; needed for
  watching live SSE previews with the artifact iframe. The daemon serves `/api`
  which the web proxies (same origin, no CORS in prod/dev on the same port).
- Media surfaces (image/video/audio with provider models) require provider config
  in the web UI or via media-config; the HyperFrames HTML→mp4 path needs none.

## Pitfalls encountered

1. **pnpm version**: system pnpm 11.21.0 → EBADENGINE risk. `corepack enable`
   fixes it; `pnpm --version` inside the repo must be 10.33.2.
2. **`od` name clash**: `/usr/bin/od` octal dump. Always use `$OD_BIN`.
3. **`od skill run` doesn't exist** — use the `/api/runs` flow (documented above).
4. **First web load is slow**: next.js dev compile takes ~30s on first request;
   subsequent loads ~100ms. Not a proxy issue.
5. **CORS / LAN access**: the daemon only trusts the web origin port. For LAN
   access, restart daemon with `OD_ALLOWED_ORIGINS=http://<lan-ip>:<webport>`
   AND proxy the web port. A plain socat TCP forward still fails CORS unless the
   origin is allowlisted.
6. **AMR/Vela warning in web UI**: harmless; it's one of 12 optional runtimes.
   Onboarding gate stuck on login → set `.od/app-config.json`:
   `"onboardingCompleted": true` (daemon reads it per request, no restart).
7. **Agent slowness**: spawned agents (opencode) can be slow/thorough (reading the
   repo's source instead of just composing). Give explicit, narrow prompts and
   "do not ask questions; produce the artifact" to keep them on task. Runs take
   5-30 min by design.
8. **media generate needs --composition-dir** for hyperframes-html; otherwise
   task fails fast with a clear error.
9. **Better not to pass --daemon-port/--web-port twice** — tools-dev restarts
   fine, keeps `.od/` data.
10. **Daemon data root**: `.od/` at repo root (RUNTIME_DATA_DIR derived from
    OD_DATA_DIR). Projects, skills, design-systems, media, runs all live there.
    Daemon data contract is in upstream `AGENTS.md`.

## Artifacts produced (this run)

- `output/landing.html` — open-design-landing skill, "default" DS, p4 Lab brand
  (98 KB, verified: screenshot 42% non-white, 242 gray levels).
- `output/open-design-intro.mp4` — hyperframes skill, 16s 1920×1080 h264 30fps
  (verified: ffprobe + OCR of frames shows real text content).
- `output/landing-brutal.html` — same skill, custom `user:ag01-brutal` DS (black bg, neon-green accent, Courier Mono). Verified: tokens present in HTML + screenshot 96% non-white + OCR readable.
