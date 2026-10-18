# e097 — Night Worker (overnight autonomous agent loop)

Stopped. The systemd timer that woke it every 30 min is disabled and a
`data/STOP` guard file makes every script exit immediately. To resume:
remove `data/STOP` and re-enable the timer (see Run).

## Product

| Surface | User action |
|---|---|
| `STATE.md` | The work queue: `- [ ]` items, `[x]` when done. Read-only history of every night. |
| `WORKER_BRIEF.md` | The worker's orders (spend ceiling, autonomy policy, how to work). |
| `report/` | Written night reports. |
| `sales/` | Sales packs built overnight. |
| `bin/` | `nudge.sh` (wake worker if work is open), `rotate_worker.sh`, `worker_guard.sh`, `send_prompt.sh`, `grind.sh`. All paths come from `needs.json`, never hardcoded. |
| `data/` | Runtime only (logs, bench outputs, sid, touch files). Never committed. |

## Architecture

```
needs.json       machine values (paths, cooldowns, ceilings) — scripts read this
bin/nudge.sh     wakes the worker session via PI WEB API when STATE.md has open items
WORKER_BRIEF.md  standing orders for the worker session
STATE.md         queue + log of nights
```

## Run

```bash
# inspect (no side effects)
cat STATE.md
# resume nights (explicit human decision only)
rm data/STOP
systemctl --user enable --now night-nudge.timer
# stop again, forever
touch data/STOP
systemctl --user disable --now night-nudge.timer night-nudge.service
```

## Rules

- Keys live in `/home/vuos/.secrets/.env`, read never written. No secret values in files or git, ever.
- `data/` is gitignored: logs, sids, bench outputs never reach GitHub.
- Public repo `github.com/g8d3/p4` holds scripts + docs + reports only.
