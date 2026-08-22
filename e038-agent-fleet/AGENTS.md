# e038-agent-fleet

Five coding agents running side-by-side in tmux windows of session `main`, used as a
collaborative fleet (video creation + crypto direction).

## Contents

- [fleet.md](fleet.md) — current fleet state (window -> arnes/modelo/proveedor) and the
  inference methodology: how to identify harness, model, and provider of an agent that
  only exists as a TUI inside a tmux pane.
- [ideas.md](ideas.md) — nine collaborative pipeline ideas for the fleet, with per-agent
  role splits.

## Fleet snapshot (2026-08-21)

| Window | Harness        | Model                     | Provider     |
|--------|----------------|---------------------------|--------------|
| 0:a0   | opencode       | Ox Alpha                  | OpenRouter   |
| 1:a1   | opencode       | Ox Alpha                  | OpenCode Go  |
| 2:a2   | opencode       | Muse Spark 1.2 Contributor | OpenCode Go |
| 3:a3   | opencode       | Muse Spark 1.2 Contributor | OpenCode Go |
| 4:a4   | command-code   | Ox Alpha                  | Command Code |
| 5:a5   | command-code   | Muse Spark 1.2 (taste-1)  | Command Code |

Window names follow the `a<number-of-window>` pattern (renamed with
`tmux rename-window`). Windows are grouped: 0-3 OpenCode, 4-5 Command Code.
