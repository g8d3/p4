# e042-funnel-fix-1 — Re-point Funnel at the banco app (2026-09-24)

Single next action from `runs/e042-meet-prep-1.md`, executed. Nothing in
`e042-bk2` was edited (no writes, no migration): only the Tailscale funnel
mapping changed (reset + re-ran `./funnel.sh`). Every cell below comes from a
command run on 2026-09-24 (`curl` local + public, `sqlite3` on `banco.db`,
`tailscale funnel status`, process list, file diff) or stays empty.
Secrets redacted: PIN and session token values are never quoted here.

## Verdict: public URL now serves the banco app, PIN login screen confirmed

The public Funnel URL returns 200 and is byte-identical to the local app root
on 9091: title "Banco Comunal", login form with PIN password input. Unauthed
`/api/report` through the public URL returns 401, so the gate holds publicly.
`banco.db` re-verified this leg at 38 members / 76 credits / 61 payments; the
authed `/api/report` match (38/76/61) is carried from `e042-meet-prep-1.md`
(verified same day, not re-run here to avoid handling the PIN).

## What was wrong (each verified this leg, before the fix)

| check | method | result | checked_at |
|---|---|---|---|
| local app healthy | `curl http://127.0.0.1:9091/` | 200 | 2026-09-24 |
| db counts | `sqlite3 banco.db COUNT(*)` | members 38, credits 76, payments 61 | 2026-09-24 |
| funnel on wrong port | `tailscale funnel status` | proxy to `localhost:3071`, tailnet-only | 2026-09-24 |
| public URL down | `curl https://vuos-hcar5000mi.tail6918b0.ts.net/` | 502, 0B | 2026-09-24 |
| stale mapping blocks script | `bash ./funnel.sh` in `e042-bk2` | rc=0 but log: listener already exists for port 443 | 2026-09-24 |

## Fix applied (funnel mapping only)

| step | method | result | checked_at |
|---|---|---|---|
| clear stale mapping | `tailscale funnel reset` | rc=0, status: No serve config | 2026-09-24 |
| re-point at banco app | `bash ./funnel.sh` in `e042-bk2` | rc=0, `/tmp/bk-funnel.log`: Available on the internet, proxy `http://127.0.0.1:9091` | 2026-09-24 |
| funnel process live | `ps aux \| grep tailscale funnel` | process running | 2026-09-24 |

## What works now (each verified this leg, after the fix)

| check | method | result | checked_at |
|---|---|---|---|
| public root serves app | `curl` public URL | 200, 39491B | 2026-09-24 |
| public equals local | `diff` public body vs `http://127.0.0.1:9091/` body | identical (both 200, 39491B) | 2026-09-24 |
| PIN login screen | `grep` public body | login form + PIN password input present, title Banco Comunal | 2026-09-24 |
| public gate holds | `curl` public `/api/report` without cookie | 401 | 2026-09-24 |

## Notes (honest, not blockers for the meeting)

- `tailscale funnel status` and `tailscale serve status` report "No serve
  config" even while the funnel process serves correctly; the public `curl`
  (200, identical body) is ground truth, not the status subcommand.
- The funnel process is ephemeral (`nohup tailscale funnel 9091`): after a
  reboot, re-run `./funnel.sh` in `e042-bk2` again and re-check the public URL.
- Data gaps from `e042-meet-prep-1.md` stand (0 valorizations, preview income
  0.0, negative box, settings endpoint returns the login PIN to authed
  callers): data work for after the call connects, untouched by this leg.

## Evidence ledger (command → fact, no invented numbers)

- `curl http://127.0.0.1:9091/` → 200 (before and after).
- `sqlite3 banco.db` → 38 / 76 / 61 (members/credits/payments).
- `tailscale funnel status` (before) → proxy `localhost:3071`, tailnet-only.
- Public URL (before) → 502 0B; (after) → 200 39491B.
- `./funnel.sh` first run → log "listener already exists for port 443".
- `tailscale funnel reset` → rc=0; `./funnel.sh` second run → rc=0, log
  "Available on the internet" proxy `http://127.0.0.1:9091`.
- `diff` public vs local bodies → identical.
- Public `/api/report` without cookie → 401.
