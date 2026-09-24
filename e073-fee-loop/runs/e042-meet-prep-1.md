# e042-meet-prep-1 — Run the monthly meeting inside the app (recon, 2026-09-24)

Recon only. Nothing in `e042-bk2` was changed (no writes, no migration,
no funnel restart). Every cell below comes from a command run on 2026-09-24
(`curl` against local uvicorn + public Funnel URL, `sqlite3` counts on
`banco.db`, `tailscale funnel status`, file reads) or stays empty.
Secrets redacted: PIN and session token values are never quoted here.

## Verdict: numbers match, app boots, public URL does NOT serve the app

`/api/report` (authed) returns exactly what `banco.db` holds:
38 members, 76 credits, 61 payments. The meeting sheet renders.
But dad cannot run the meeting in the app today: the public Funnel URL
answers 502 and currently proxies another port, not the banco app.

## What works (each verified this leg)

| check | method | result | checked_at |
|---|---|---|---|
| local boot | `uvicorn app:app --port 9091`, `GET /` | 200, ~11ms | 2026-09-24 |
| login gate | `POST /api/login` wrong PIN then stored PIN | 401 then `{"ok":true}` | 2026-09-24 |
| unauth blocked | `GET /api/report`, `/export/reunion.csv` without cookie | both 401 | 2026-09-24 |
| overview counts | `GET /api/overview` authed | 38 members, 76 credits | 2026-09-24 |
| report counts | `GET /api/report` authed | 38 members, 76 credits, 61 payments (summed over credit payment lists) | 2026-09-24 |
| db counts | `sqlite3 banco.db COUNT(*)` | members 38, credits 76, payments 61, purchases 721, valorizations 0, solidarity 0, fines 0, expenses 0 | 2026-09-24 |
| credit kinds | `GROUP BY kind` on credits | ordinario 20, pronto 21, distribucion 35 | 2026-09-24 |
| date span | `MIN/MAX(date)` | credits 2025-08-08..2026-08-08; payments 2025-11-07..2026-08-08; purchases 2024-11-08..2026-08-08 | 2026-09-24 |
| valorizacion preview | `GET /api/valorizacion/preview?month=` x6 months | 200 every month (see gap below) | 2026-09-24 |
| exports | `GET /export/creditos.csv|reunion.csv|acciones.csv` authed | 200: 9218B, 4187B, 45074B, Excel BOM headers present | 2026-09-24 |
| meeting UI | `static/index.html` tab ids | 8 tabs: inicio, socios, creditos, pagos, ahorros, reunion, valor, ajustes | 2026-09-24 |
| history | nested `git log` in e042-bk2 | 6 commits (import + auth + funnel script + fixes) | 2026-09-24 |
| funnel URL reachable | `curl https://vuos-hcar5000mi.tail6918b0.ts.net/` | responds, but 502 0B (see blocker) | 2026-09-24 |

## What is missing for dad to run the meeting in the app

| # | gap | evidence | checked_at |
|---|---|---|---|
| 1 | public URL does not serve the banco app | `tailscale funnel status` shows tailnet-only proxy to `localhost:3071`, not 9091; root URL returns 502; no funnel process for 9091; local app on 9091 is healthy, so the break is the funnel mapping, not the app | 2026-09-24 |
| 2 | no month ever closed | `valorizations` table 0 rows; `action_value` still at initial value; `last_valorization` null in `/api/report`; all 38 gains read 0 | 2026-09-24 |
| 3 | month-close math yields zero income | preview returns `interests_total` 0.0 for all 6 months probed (2025-11, 2025-12, 2026-06, 2026-07, 2026-08, 2026-09); sampled payment rows carry principal with interest 0.0 (imported lump sums, interest never split) so any valorization saved today computes delta 0 | 2026-09-24 |
| 4 | distribution pool empty | `/api/report`: box negative (money_out exceeds money_in), `per_member` 0.0, only 2 eligible members without active credit; all 76 credits read active (`done` 0) | 2026-09-24 |
| 5 | monthly solidarity/fines/expenses unrecorded | solidarity 0 rows, fines 0 rows, expenses 0 rows, though model expects monthly solidarity per member | 2026-09-24 |
| 6 | settings endpoint leaks the gate | `GET /api/overview` returns the login PIN inside `settings` to any authed caller; hide it before the URL is shared wider | 2026-09-24 |

## Single next action

Re-run `./funnel.sh` in `e042-bk2` (re-points Funnel at 9091) and reload the
public URL on dad's phone: if the PIN screen appears, the meeting can run in
the app; everything else (close a month, split interest per payment, balance
the box) is data work for after that call connects.

## Evidence ledger (command → fact, no invented numbers)

- `curl http://127.0.0.1:9091/` → 200 (boot ok).
- `curl -X POST /api/login` → `{"ok":true}` with stored PIN; 401 without.
- `sqlite3 banco.db`: 38 / 76 / 61 / 721 / 0 (members/credits/payments/purchases/valorizations).
- `/api/report` JSON: members 38, credits 76, payments 61, rows 38, gains 38, `last_valorization` null, `per_member` 0.0, eligible 2.
- `/api/valorizacion/preview?month=...` x6 → `interests_total` 0.0, `delta` 0.0 every month.
- `tailscale funnel status` → proxy target is another local port, funnel URL → 502.
