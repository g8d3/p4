# ag-01 — Setup, exploration & benchmark

Full-stack agent for the Open Design experiment: install per the quickstart,
explore the `od` CLI + skill catalog until the toolset is understood, run
skills to produce real artifacts, integrate with OpenCode (`od mcp install
opencode`), and benchmark where Open Design fits in the p4 pipeline. You are
the only agent here — keep notes as you go (`output/exploration.md`) or the
next run loses your context.

## Model

`opencode -m opencode-go/deepseek-v4-flash` (priority 1).

## Mission

1. **Install** — `git clone https://github.com/nexu-io/open-design` into
   `../upstream/` (depth 1), then per the quickstart: `pnpm install` and
   `pnpm tools-dev`. Read the repo's `QUICKSTART.md` before assuming anything.
2. **Verify** — confirm the daemon, web UI, and `od` CLI actually work:
   `od --version`, `od skills list`, `od project list --json`, check the ports
   and processes are really listening. Trust nothing until you see output.
3. **Explore** — document the skill catalog, plugins, `open-design.json`
   spec fields (`od.kind`, `od.mode`, `od.taskKind`, `od.inputs`), and the
   CLI surface (`od --help`, every subcommand). Which skills work headless vs
   need the web UI? Which modes generate web, deck, dashboard, video?
4. **Run skills → artifacts** — `od skill run open-design-landing --output
   ./output/landing.html` (or equivalent). Run at least one more output mode
   (deck, dashboard, or video). Verify every artifact is real: open the HTML
   in headless Chrome, screenshot it, confirm readable non-stub content.
   Apply a `DESIGN.md` brand system and re-render to confirm tokens propagate.
5. **Integrate with OpenCode** — run `od mcp install opencode` and document
   exactly what it changes (config files, MCP snippet). Test whether the MCP
   server is usable from an OpenCode session if feasible.
6. **Benchmark** — write `output/benchmark.md`: where Open Design fits in p4
   (HTML capture source for videos, brand consistency, decks/landings, Hyper
   Frames vs e018), compared with p4's existing headless-Chrome slides path and
   KIE image pipeline. Real numbers and commands, not vibes.
7. **Wrap up** — write `output/exploration.md` (how to start, agent-critical
   commands, offline vs web-UI requirements, pitfalls), `output/metadata.json`
   per fundamentals, `done.txt`, and `notify.sh done "..."`.

## Success criteria

- `od` CLI responds and `pnpm tools-dev` runs the daemon + web UI (verify
  with processes/ports, not just command exit codes).
- At least two real artifacts rendered by skills (one landing, one other mode),
  each verified by screenshotting the HTML in headless Chrome (non-blank,
  readable).
- `output/exploration.md` answers: how to start, which commands are
  agent-critical, headless vs web-UI requirements, and the `open-design.json`
  spec in practice.
- `output/benchmark.md` states with evidence whether Open Design should be
  adopted, adapted, or ignored by p4 — and why.

## Pitfalls (check before assuming)

- **pnpm version**: the repo pins pnpm 10.33.x via `packageManager`/lockfile;
  system pnpm is 11.21.0. Enable/pin via corepack (`corepack enable` +
  re-verify `pnpm --version` inside the repo) or `pnpm install` may fail with
  EBADENGINE or use the wrong lockfile.
- **Desktop app is macOS/Windows** — on Linux we run from source. Do not
  assume the desktop installer applies.
- **`od` name clash**: `/usr/bin/od` is the octal-dump utility. Prefer the
  Open Design `od` via its installed path / project scripts, or alias it. If
  `od --help` shows octal dump help, you're hitting the wrong binary.
- **Ports**: `pnpm tools-dev` may complain if a port is taken — pass
  `--daemon-port` / `--web-port` per QUICKSTART.md.
- **Install is heavy** — `pnpm install` on a monorepo can take minutes. Run it
  in background with a self-wake; never block on it.
- **Node 24 required** — Node 22 is unsupported; we have v24.16.0, fine.
- **Learn the tool first**: read `QUICKSTART.md` and `od --help` fully before
  driving commands. Re-read docs when something fails; don't invent
  workarounds.
- The repo is a moving target — if documented commands differ from live
  behavior, trust the live `od --help` and report the delta.

## Self-command

- Every blocking command runs in background: `> /dev/null 2>&1 &`
- After each command, self-wake:
  `tmux send-keys -t 27-1 "check status" Enter` (Enter is required)
- Never leave a command without a timeout or self-wake.

## Inherits

- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles,
  command rules, background + self-wake pattern, Chrome/CDP, video pipeline
- [../AGENTS.md](../AGENTS.md) — experiment scope, setup, repo layout
