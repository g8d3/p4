# ag-07 — On-demand thinking partner

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Model
`opencode-go/deepseek-v4-flash` (fast, cheap for brainstorming)

## Purpose

This agent has no fixed task. It exists to:

- Read and understand any program in the p4 ecosystem
- Generate ideas for integration, refactoring, or unification
- Improve existing tools (pdw, nimbo, filex, etc.)
- Record videos on demand of whatever we discuss
- Research, prototype, or implement new features on the fly

## What's available

### p4 — Experiments at `/home/vuos/code/p4/`
- `e010-more-videos/ag-00/bin/pdw` — display manager
- `e010-more-videos/ag-00/bin/record.sh` — recording pipeline
- `e010-more-videos/ag-04/GUIA.md` — unified platform plan
- `e010-more-videos/ag-04/PENDIENTES.md` — future improvements

### p3 — Projects at `/home/vuos/code/p3/`
- `s84/nimbo/` — Python web framework (CRUD, WS, proxy, dashboard)

### Other tools
- `/home/vuos/code/filex/serve_md.py` — file server
- `/home/vuos/.local/bin/nova-chrome` — chrome launcher (X11, not Wayland)

## To record a video

Use `../ag-00/bin/pdw` for display management and recording:

```bash
../ag-00/bin/pdw init                # ensure sway is running
../ag-00/bin/pdw ds new              # create a display
../ag-00/bin/pdw w new HEADLESS-N foot --maximized  # open terminal
../ag-00/bin/pdw rec HEADLESS-N 30 demo-name  # record
```

## Output

- Written output (code, docs, ideas): save in this directory
- Videos: save in `./output/<topic>/`
