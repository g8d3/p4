# e067-sys-panel — ports + cron + systemd + repos panel

Local ops dashboard: which apps use which ports, all cron jobs, systemd services,
and the repo tree (which git checkouts exist, what each is, sync state).
Single FastAPI file + vanilla JS. Mobile-friendly. Port **8326**.

## Run

```bash
cd e067-sys-panel && python3 app.py        # → http://localhost:8326
bin/healthcheck.sh                          # restart if down (cron cada 15 min)
```

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

- `*/15 * * * * .../bin/healthcheck.sh` → `server.log` # e067-healthcheck (ignored)
- `@reboot cd .../e067-sys-panel && python3 app.py >> server.log 2>&1` # e067-reboot

## Repos tab (no polling)

`/api/repos` scans every git checkout under `$E067_REPOS_ROOT` (default
`/home/vuos/code/p4`). Sync changes (commit, push, pull, branch switch) reach
the open page through the existing SSE watcher (`/api/events` → `repos`
version): the fingerprint is HEAD/index/branch-tip mtimes only, no git
subprocesses, checked ~every 15s. The 30s tab fallback stays as safety net.
The kind rule lives in `REPOS.md` at repo root: new code goes in `p4/<exp>/`,
a separate repo only if something deploys from it.
