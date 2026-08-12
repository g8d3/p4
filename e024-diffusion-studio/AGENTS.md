# e024 — Diffusion Studio editor (video editor for coding agents)

Experiment to set up and play with **Diffusion Studio's open-source editor**
([diffusionstudio/editor](https://github.com/diffusionstudio/editor), v0.132.0) —
a video editor built for coding agents. An agent writes a composition in TSX,
the `dapi` CLI mounts it into the editor, and every element stays editable. The
pitch: "FFmpeg for agents", with generative AI and multimodal understanding
built in.

## Why this experiment

p4 already has a complete ffmpeg/VAAPI/Parakeet/KIE video pipeline. Diffusion
Studio is a potential programmatic alternative or complement: compositions as
code, a typed scene graph, browser-based GPU rendering (WebCodecs), and
agent-native CLI conventions (JSON/JSON Lines on stdout, errors on stderr,
exit code 1). This experiment evaluates where it fits in p4 and what it does
better or worse than the current pipeline — including whether `dapi node
render` can replace or feed the ffmpeg composition step.

## Repo layout

The upstream source lives in `upstream/` (git-cloned, depth 1). It is
**ignored by the p4 git repo** (see `.gitignore`) — do not commit it.

| Path | Package | What it is |
|---|---|---|
| `apps/web` | `@diffusionstudio/web` | The editor UI (Solid + Vite) |
| `apps/desktop` | `@diffusionstudio/desktop` | Electron shell hosting the editor |
| `apps/cli` | `@diffusionstudio/cli` | The `dapi` CLI |
| `packages/jsx` | `@diffusionstudio/jsx` | JSX runtime, types, and generated assets (`generate.*`) for compositions |
| `examples/` | — | Runnable compositions (basics, genai, ticker, HTML-in-canvas, three.js, WebGPU) |
| `reference/` | — | `dapi` CLI reference + JSX composition markup reference |

## Core workflow

```sh
dapi open                       # launch the editor (use -b to run headless)
dapi mount hero.tsx             # compile + mount a TSX composition
dapi node render -o hero.mp4    # encode a scene to disk
```

Key `dapi` commands:

| Command | Purpose |
|---|---|
| `dapi open` | Launch the app, open a file, or turn a folder of footage into a project |
| `dapi context` (`ctx`) | Summary of the open project: scenes, playhead, fonts |
| `dapi mount` | Compile and mount a JSX composition |
| `dapi node …` | Scene graph: `ls`, `tree`, `grep`, `patch`, `insert`, `cp`, `rm`, `capture`, `render` |
| `dapi asset …` | Media library: `add`, `ls`, `tree`, `mv`, `rm`, `export` |
| `dapi media …` | Inspect a file: `probe`, `grab`, `filmstrip`, `waveform`, `transcribe`, `listen` |
| `dapi project …` / `folder …` / `selection …` | Projects, library folders, canvas selection |
| `dapi models` / `voices` / `fonts` | Discover generation models, speech voices, local fonts |
| `dapi fetch` | Download a video from yt/tt/ig, ready for `dapi asset add` |

Conventions: single results are one JSON value, collections are JSON Lines,
errors go to stderr with exit code 1. Everything is built to be piped, grepped,
and driven by a program.

## Local setup

Requirements: Node 20+ and npm. Current machine: node v24, npm 12.

```sh
cd upstream
npm install
cp apps/web/.env.example apps/web/.env   # required: the app won't run without it
npm run dev:web        # editor in the browser (Vite dev server)
# or
npm run dev:desktop    # Electron shell: builds the CLI, starts the web server, launches the app
```

Link `dapi` on PATH once:

```sh
npm run symlink:create --workspace=@diffusionstudio/cli
```

> **Note**: the repo ships a hosted backend default in `.env.example`
> (`VITE_API_URL=https://api.diffusion.studio`, Supabase). Playground work may
> require an account (`dapi whoami`) and the app talks to the hosted API for
> auth/assets. Verify what actually works offline before assuming anything.

## Experiment goals

1. Get the editor running locally and `dapi` working.
2. Explore the full CLI surface and document commands + pitfalls.
3. Write compositions (TSX) and render real videos to disk.
4. Integrate with the p4 pipeline: KIE Gemini TTS narration, Parakeet
   transcription, real footage from the p4 capture stack.
5. Benchmark vs the ffmpeg/VAAPI composition pipeline (speed, quality, cost).

## Files / agents

| Path | What it is |
|---|---|
| `ag-01/` | Single full-stack agent: setup, exploration, TSX compositions, renders, benchmark vs the ffmpeg/VAAPI pipeline |

Agent outputs go in `ag-01/output/` (gitignored). Composition sources and notes
are committed alongside the AGENTS.md so the experiment's state is auditable.

## Inherits

- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — conventions,
  video pipeline, GPU/VAAPI encoding, command rules
