# e086 — Agent Company OS (the app that runs its own team)

Web app to manage AI agent teams. Everything is set up from the web app —
**no env vars**. A supervisor loop guarantees at least 1 agent is working;
if none is, it starts one or more automatically. The app shows the
**past, present and future** of the build plus **iterations (versions)**.
It acts as a complete business team: design, implement, review (e2e incl. UI),
content, provisioning, growth — with **dynamic roles** the CEO / Board can
redefine live.

## Product

| Surface | User action |
|---|---|
| Board | Past / Present / Future + activity log. Work walks itself left; Start/Finish/Release/Reopen hurry it. The core view. |
| Team | Agents (spawn/beat/stop), tasks, and the org chart — CEO/Board redefines roles here. Supervisor auto-starts if working < min. |
| Versions | Plan → release versions with notes; 📸 ties a version to restorable code. Releasing stamps all finished unclaimed tasks with the version — a version IS its tasks. Row carries {claimed, snapshot, by}; tasks.version is the foreign key. Released = Past, planned = Future. |
| System | Settings (no env vars) + operator powers: restart, daemon, logs, code editor, gate. |
| `POST /api/loop/tick` | Supervisor: ≥ `min_workers` fresh workers (auto-start + reap dead), idle hands pull backlog, orphans drift back. No theater: only `action` tasks self-complete (by executing); the rest hold for a real builder, human Finish certifies; holders rotate after `hold_rotate_ticks`. |
| Task `action`s | `add_task`, `add_role`, `update_settings`, `snapshot`, `release` (cuts a released version + code snapshot). Unknown actions → `needs_human`, never fake-done. |
| CEO review (every `ceo_every_ticks`) | Failing verify checks → repair proposals; code newer than last release → a `release` task that cuts a real version itself. |
| Builder bridge | External agents drive work via API: heartbeat to stay fresh, `POST /api/tasks {advance, result}` to certify done with notes. Human Finish = same certification. Full machine-readable contract: `GET /api/docs`. |
| Sessions (`GET /api/sessions`, Team 🕘) | Full per-agent history: spawned by whom/when, heartbeat count + first/last, every task held with outcome, ended when/why. Survives reaping and deletion. |
| UI constitution (gate-enforced) | nav == sections, no duplicate ids, every `onclick` resolves to a defined function, every item actionable or coaching empty-state. Redundancy is a bug. |
| `GET /api/verify` | E2E self-review: settings, roles, min-workers, UI first-paint, iterations. |

## Architecture

```
server/app.py      stdlib only (ThreadingHTTPServer) + /api/*
public/index.html  single-file UI, 4 tabs, 2s refresh, zero deps
needs.json         default machine values (port/bind/loop/timeout/min_workers)
data/settings.json web-saved overrides (wins; no env vars ever read)
data/roles.json    dynamic org chart (CEO/Board editable)
data/agents.json   id/name/role_id/status/heartbeat/task
data/tasks.json    todo/doing/done + action/result/needs_human, each bound to a role
data/sessions.json  per-agent session history (spawn/beats/tasks/ended)
data/iterations.json  planned/released versions
data/events.jsonl  append-only log (boot/tick/auto_start/...)
data/loop_state.json  running/ticks/auto_starts/last_tick
bin/serve.sh       start server (port from settings/needs)
bin/loop.sh        one | daemon — supervisor ticks (web Ops tab adopts via data/loop.pid)
bin/restart-detached.sh  web-triggered restart (kill PID + boot, survives old process)
test/check.sh      GATE GREEN = health+roles+timeline+verify+auto-start+paint (runnable from Ops tab)
data/snapshots/<id>/  restorable code versions (server/ public/ needs.json AGENTS.md)
```

Rule: stdlib only, no deps. Machine values from settings/needs — never env, never buried.

## Run

```bash
bash bin/serve.sh            # port from needs.json (8361)
bash bin/loop.sh one         # one supervisor tick
bash bin/loop.sh daemon      # keep ticking every loop_interval_sec
bash test/check.sh           # GATE GREEN
```
