# Your models (2026-10-30)

You picked **4**. Everything else in the picker is bloat the old guard baked in —
providers kept adding models and the snapshot silently grew to 162. That bloat is
gone; this file is the record of what you chose.

| # | Model | Role |
|---|---|---|
| 1 | `opencode-go/muse-spark-1.3-contributor` | Daily driver. Also the default (`defaultProvider: opencode-go`, `defaultModel: muse-spark-1.3-contributor`, thinking `high`). |
| 2 | `opencode-go/deepseek-v4.1-flash` | Fast cheap fallback on the opencode-go proxy. |
| 3 | `opencode-go/iceman-contributor-free` | Free contributor-tier fallback. |
| 4 | `opencode-go/beam-free` | Free fallback. |

## Where this lives

- The picks: `wanted.json` next to this plugin's data
  (`~/.pi-web/plugin-data/p4-models/wanted.json`). Only you edit it — by hand
  or with `scripts/models.py want ...`.
- The enforcement: `../models/models.js`. On every check (daemon start, then
  once a minute) it puts back any pick missing from
  `~/.pi/agent/settings.json` and logs the repair. It never removes anything
  and never changes `wanted.json` by itself.
- Changing your picks: edit `wanted.json`, then `python3 scripts/models.py sync`
  to trim the settings file down to exactly your picks (a backup is kept first).

## What the old design got wrong

The first version kept a `canonical.json` snapshot that auto-grew to whatever
was biggest, and "repaired" any drop of 5+ models. On 2026-10-30 that logic
fought you directly: at 14:52 and 14:53 it rewrote your deliberate 4-model edit
back to 162 models, twice in one minute (see the `settings-before-repair-*`
backups and `drift.jsonl`). A heuristic cannot tell a collapse from a decision;
an explicit list can. `canonical.json` is retired — kept on disk as history,
no longer read.
