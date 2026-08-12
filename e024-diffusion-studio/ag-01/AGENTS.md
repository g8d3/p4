# ag-01 — Setup & exploration

Set up the Diffusion Studio editor from `../upstream/` and explore the `dapi`
CLI until the whole toolset is understood, working, and documented. You are the
first person to touch this experiment — verify everything, trust nothing.

## Model

`opencode -m opencode-go/deepseek-v4-flash` (priority 1).

## Mission

1. **Install** — `npm install` in `../upstream/`, copy `.env.example` → `.env`,
   and get the editor running. Try `npm run dev:web` first (browser mode,
   fewer moving parts than Electron). Link `dapi` on PATH via
   `npm run symlink:create --workspace=@diffusionstudio/cli`.
2. **Verify** — `dapi open -b` (headless) or with a display, then `dapi
   whoami`, `dapi context`, `dapi models`. Confirm the CLI actually talks to
   the app over the local socket before trusting any output.
3. **Explore** — read `../upstream/reference/` (every command) and
   `../upstream/examples/` (runnable compositions). Try the examples:
   `dapi mount ../upstream/examples/01-basics.tsx`, `dapi node tree`, `dapi
   node capture`, `dapi node render -o <out>.mp4`.
4. **Document** — write your findings to `output/exploration.md`: what works,
   what fails, exact commands with their real outputs, and pitfalls. Keep
   `bin/` for any helper scripts you write.

## Success criteria

- `dapi` responds on the linked PATH and `dapi node render` produces a real
  `.mp4` on disk (verify with `ffprobe` — resolution, duration, no black).
- `output/exploration.md` exists and answers: how to start the app, which
  commands are agent-critical, what needs the hosted backend vs works offline,
  and how `dapi node render` encodes (codec, hardware) vs the p4 VAAPI rule.

## Pitfalls (check before assuming)

- The app may need `apps/web/.env` (Supabase + API keys) or it won't run —
  the example file exists in the repo, copy it.
- `dapi` talks to a **running app** over a local socket. Commands fail if the
  app isn't up. Check `dapi logs` and the socket before debugging the CLI.
- `dapi node render` renders in the browser engine (WebCodecs) — verify the
  encoder tag with ffprobe before comparing it to the p4 h264_vaapi rule.
- `npm install` on 5 workspaces can take minutes and print warnings. Background
  it with a self-wake instead of blocking.
- The repo is a moving target (v0.132.0); if a documented command has no
  reference file or differs from `reference/`, trust the live `dapi --help`.

## Self-command

- Every blocking command runs in background: `> /dev/null 2>&1 &`
- After each command, self-wake:
  `tmux send-keys -t <window> "check status" Enter` (Enter is required)
- Never leave a command without a timeout or self-wake.

## Inherits

- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles,
  command rules, background + self-wake pattern, GPU/VAAPI encoding
- [../AGENTS.md](../AGENTS.md) — experiment scope, repo layout, core workflow
