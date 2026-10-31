# e106 — pi engine extensions (not PI WEB plugins)

Real files live here, versioned. `~/.pi/agent/extensions/` holds only
symlinks pointing at this directory — the reverse of nothing: pi loads
whatever is in that folder on every launch, so the file must be reachable
there, but the truth lives here.

## Contents

| File | What |
|---|---|
| `sync-opencode-models.ts` | Merges live OpenCode Zen + Zen Go model lists into pi's catalog at every pi launch, and enables models in `settings.json`. Honors the model guard's picks (`~/.pi-web/plugin-data/p4-models/wanted.json`): with picks recorded it enables exactly those, otherwise everything discovered. |

## Rules

- Edit here, never in `~/.pi/agent/extensions/` (that's a link farm).
- After any change: run `pi -p "Reply with exactly: ok"` from `/home/vuos`
  and confirm the `[sync-opencode-models]` line plus `doctor.sh models`
  still exact-match — a broken extension breaks every pi launch.
