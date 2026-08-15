# e027 — Open Design (open-source design engine for coding agents)

Experiment to set up and play with **Open Design** ([nexu-io/open-design](https://github.com/nexu-io/open-design),
[open-design.ai](https://open-design.ai/quickstart/)) — the open-source "Claude
Design alternative". It turns a local coding agent into a design engine driven
by **composable skills** + portable **`DESIGN.md` brand systems**. It generates
web / desktop / mobile prototypes, live dashboards / artifacts, decks, images,
video, and **HyperFrames** motion graphics — with a local daemon (`od`), a web
UI, and a stdio MCP server.

The pitch: *"design and code as one living artifact"* — the agent writes the
canonical project files (HTML/code/tokens in the repo), you iterate by talking,
and the design never drifts from the code.

## Why this experiment

Open Design is directly relevant to p4 on several axes:

- **It runs on OpenCode** — `od mcp install opencode` is a first-class adapter.
  This is the first design engine we test that plugs into p4's own agent.
- **HyperFrames output mode** — p4 already has `e018-hyprframes-browser-video`;
  Open Design lists HyperFrames motion graphics as one of its modes.
- **Video / deck / dashboard generation** — competes with and complements the
  p4 KIE/ffmpeg/VAAPI pipeline (generated HTML → capture → h264_vaapi).
- **DESIGN.md brand systems** — a possible source of consistent brand rules
  across p4's videos, slides, and landing pages.
- **Local-first, open source, BYOK** — artifacts live in our repo, not in a
  vendor's database.

## Setup (quickstart: open-design.ai/quickstart)

Requirements already satisfied on this machine: Node 24 (v24.16.0), corepack,
pnpm (11.21.0 — the repo pins 10.33.x via `packageManager`/lockfile; corepack
must pick up the pinned version, verify with `pnpm --version` inside the repo).

```sh
git clone https://github.com/nexu-io/open-design   # → upstream/ (gitignored)
cd upstream
pnpm install                                       # workspace deps
pnpm tools-dev                                     # start daemon + web UI
```

First artifact (drive the daemon directly with the `od` CLI):

```sh
od skill run open-design-landing --output ./artifact.html
```

Full notes live in the repo's `QUICKSTART.md` — read it before assuming.

## Repo layout

The upstream source lives in `upstream/` (git-cloned). It is **ignored by the
p4 git repo** (root `.gitignore`) — do not commit it. Notes and deliverable
sources are committed so the experiment is auditable.

## Experiment goals

1. **Install per quickstart** — clone, `pnpm install`, `pnpm tools-dev`, verify
   the daemon + web UI + `od` CLI actually respond (scepticism: check ports,
   processes, `od --version`).
2. **Explore the CLI + skill catalog** — `od skills list`, `od plugin list`,
   `od project list`, the web UI skill catalog. Document what skills exist,
   which need the daemon/web UI vs work headless, and the `open-design.json`
   spec fields (`od.kind`, `od.mode`, `od.taskKind`, `od.inputs`).
3. **Run skills → real artifacts** — `od skill run` a landing page and at
   least one more output mode (deck, dashboard, or video). Verify the HTML is
   real, renderable content (open in headless Chrome / screenshot), not a
   stub.
4. **Integrate with OpenCode** — `od mcp install opencode`; document what it
   changes and whether the MCP server is usable from a p4 agent session.
5. **Design systems** — pick or create a `DESIGN.md`, render the same artifact
   with different brand systems, confirm the tokens propagate.
6. **Evaluate vs p4 pipeline** — where does Open Design fit: HTML capture
   source for videos, brand consistency, deck/landing production? Compare with
   p4's existing slides-to-PNG headless Chrome path and KIE image pipeline.
   Write the verdict to `output/benchmark.md` with evidence.

## Files / agents

| Path | What it is |
|---|---|
| `ag-01/` | Full-stack agent: setup, exploration, skill runs, OpenCode integration, benchmark |

Agent outputs go in `<agent>/output/` (gitignored). Notes and deliverable
sources are committed so the experiment's state is auditable.

## Inherits

- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — conventions,
  command rules, background + self-wake pattern, Chrome/CDP, video pipeline
