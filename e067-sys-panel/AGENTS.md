# e067-sys-panel — ports + cron + systemd + repos panel

Local ops dashboard: which apps use which ports, all cron jobs, systemd services,
and the repo tree (which git checkouts exist, what each is, sync state).
Single FastAPI file + vanilla JS. Mobile-friendly. Port **8326**.

## Run

```bash
systemctl --user status e067-sys-panel       # systemd owns it (Restart=always)
```

No cron, no healthcheck script, no reboot line: with user lingering on,
the enabled unit starts at boot and systemd restarts it on death — the OS
is the supervisor, via process events (SIGCHLD), not a timer.
`bin/healthcheck.sh` stays on disk, unused.

## What it does

| Tab | Source of truth | Read | Write |
|---|---|---|---|
| 🔌 Puertos | live `ss -tlnp` + `/proc` + HTTP probe | auto-scan | kill pid, launch cmd, registry CRUD (`ops.db`) |
| ⏰ Cron | `crontab -l`, `/etc/crontab`, `/etc/cron.d`, `cron.{hourly,daily,weekly,monthly}`, `systemctl list-timers` | all shown | user crontab only (add/edit/toggle/run-now); system = read-only |
| ⚙️ Servicios | `systemctl list-units --type=service` (system + user) | all shown | start/stop/restart/enable/disable; full CRUD for `~/.config/systemd/user/*.service` |
| 📊 Stats | 1s sampler (`/proc`) → OHLC candles per timeframe | CPU/RAM/NET/DISK/LOAD charts | candle count configurable per timeframe (saved in browser) |
| 🗂 Repos | live `git` scan of the workspace (`/api/repos`, 30s cache) | every checkout: kind (ours/upstream/worktree/local-clone), branch, sync | read-only (the fix happens in a terminal) |

- **AI description**: rule-based Spanish one-liners (`PATTERNS` in app.py);
  if `OPENCODE_GO_API_KEY` exists, `/api/describe` tries the LLM first.
- Extra port action beyond matar/visitar: **🔍 inspeccionar** (cwd, env filtrado, conexiones) + **📋 copiar comando** + **▶ relanzar**.
- **Speed (caché en 2 capas)**: backend TTL in-memory (ports 4s, cron/services 5s, logs 10s, inspect 2s; se invalida en cada mutación) + frontend SWR (pinta caché al instante y refresca en fondo; ⚡ = vino de caché). Medido: `/api/ports` 2.3s → 7ms en hit.
- **Live updates**: watcher cada 3s (huellas de `ss`, `crontab -l`, `systemctl`) → `/api/events` (SSE) empuja versiones; la pestaña visible se recarga sola con flash `⟳ … cambió en el sistema` + punto ● verde. Stats se auto-refresca cada 3s; resto cada 30s como respaldo.
- **Stats**: sampler 1s (CPU `/proc/stat`, RAM `MemAvailable`, red rx/tx KB/s sin `lo`, disco `/` + `/home`, load1) → velas OHLC en 1s/30s/5m/1h/8h/1d (defaults 60,10,10,10,10,10, máx 500, configurables). Persisten en `ops.db:stat_candles` cada 60s; timeframes largos se llenan solos con el tiempo.

## Files

- `app.py` — whole backend
- `static/index.html` — whole frontend (3 tabs, no build)
- `ops.db` — manual app registry (ignored by git)
- `*.log`, `crontab.bak` — runtime artifacts (ignored)

## Cron

None. (Was: healthcheck every 15 min + @reboot — removed 2026-10-30,
systemd `Restart=always` replaces both.)

## Repos tab (events, not polling)

`/api/repos` scans every git checkout under `$E067_REPOS_ROOT` (default
`/home/vuos/code/p4`). A thread blocks on the kernel's inotify stream for
every checkout's git metadata (same ctypes pattern as likes_web); a commit,
push, pull, fetch or branch switch wakes it and the open page refreshes over
the existing SSE channel. Nothing git-related runs on a timer. New checkouts
appear on next tab open / rescan. `↓ fetch all` runs `git fetch` in every
`ours` repo in background; FETCH_HEAD moves, inotify fires, the table updates
itself.

Honest limits: `↓ behind` for GitHub-side moves is unknowable without asking
— fetch is the ask, and it only runs on your click. The ports/cron/services
watcher beside it still ticks (3s/5s): the kernel emits no file event for "a
process started listening", so that one stays a cheap `ss` look.
