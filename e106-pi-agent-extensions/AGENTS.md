# e106 — pi engine extensions (not PI WEB plugins)

Real files live here, versioned. `~/.pi/agent/extensions/` holds only
symlinks pointing at this directory — the reverse of nothing: pi loads
whatever is in that folder on every launch, so the file must be reachable
there, but the truth lives here.

## Contents

| File | What |
|---|---|
| `sync-opencode-models.ts` | Merges live OpenCode Zen + Zen Go model lists into pi's catalog at every pi launch, and enables models in `settings.json`. Honors the model guard's picks (`~/.pi-web/plugin-data/p4-models/wanted.json`): with picks recorded it enables exactly those, otherwise everything discovered. |
| `pi-web-restart` | 3-second front-door restart (linked from `~/.local/bin`). Sessions untouched. |
| `pi-web-restart-resume <session-id> [cwd] [message]` | One-line daemon restart + resume. Detached ~5s, waits healthy, prompts the session to continue from its transcript. Default message suffices for routine use. |

## Rules

- Edit here, never in `~/.pi/agent/extensions/` (that's a link farm).
- After any change: run `pi -p "Reply with exactly: ok"` from `/home/vuos`
  and confirm the `[sync-opencode-models]` line plus `doctor.sh models`
  still exact-match — a broken extension breaks every pi launch.
