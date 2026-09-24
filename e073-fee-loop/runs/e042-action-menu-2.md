# e042-action-menu-2 — paid-action menu LIVE (builder leg, 2026-09-24)

Status: DONE. Two priced paid actions live in the app with one-click
buttons on the PIN screen + Inicio, no login. Every cell below comes from
a command run on 2026-09-24 (`curl` local 9091 + public funnel URL,
`grep`/`cmp`/`md5sum` on fetched roots, test POSTs, read-only
`SELECT count(*)` on the live DB, `stat`/`md5sum` on `banco.db`).
No PIN quoted.

## What was built (one fact per column)

| fact | value | checked_at |
|---|---|---|
| priced paid actions | 2: copia-extracto $5000, paz-y-salvo $10000 | 2026-09-24 |
| backend | auth-exempt POST /api/action → runs/e042-actions.jsonl (same pattern as /api/refer) | 2026-09-24 |
| frontend | menu block id=action-menu (Inicio) + id=action-menu-pin (PIN screen), one-click data-action buttons, no login | 2026-09-24 |
| files changed | ../e042-bk2/app.py, ../e042-bk2/static/index.html | 2026-09-24 |
| app reboot | 9091 rebooted, new root 46760B (was 44940B) | 2026-09-24 |

## Menu markers via curl (one fact per column)

| fact | value | checked_at |
|---|---|---|
| local root | 200, 46760B | 2026-09-24 |
| public root | 200, 46760B | 2026-09-24 |
| local vs public roots | byte-identical (cmp identical, md5 e2ce23f84034a86bc36758a95d41e489 both) | 2026-09-24 |
| menu markers local | 8 (action-menu x2, api/action x1, data-action x5) | 2026-09-24 |
| menu markers public | 8 (same grep, same counts) | 2026-09-24 |

## Action endpoint round-trip (one fact per column)

| fact | value | checked_at |
|---|---|---|
| local POST /api/action copia-extracto | 200 {"ok":true,"price":5000} | 2026-09-24 |
| public POST /api/action paz-y-salvo | 200 {"ok":true,"price":10000} | 2026-09-24 |
| bad action local | 400 {"detail":"unknown action"}, no log write | 2026-09-24 |
| test rows round-tripped | 2 (both source=test-leg), then removed | 2026-09-24 |
| runs/e042-actions.jsonl | 0 bytes, 0 rows (0 real rows) | 2026-09-24 |
| real paid actions | PENDING — menu live, no stranger row yet | 2026-09-24 |

## Gates + live DB untouched (one fact per column)

| fact | value | checked_at |
|---|---|---|
| local /api/report unauth | 401 (gate intact) | 2026-09-24 |
| public /api/report unauth | 401 (gate intact) | 2026-09-24 |
| live valorizations | 0 rows | 2026-09-24 |
| banco.db mtime | 2026-08-23 (pre-leg, unchanged) | 2026-09-24 |
| banco.db md5 | ba22f042f4ee2d8c6eef337f5604941d (same before/after) | 2026-09-24 |
| runs/e042-referrals.jsonl | 0 bytes (gate-check temp row removed) | 2026-09-24 |

Next: drive the first stranger to tap a paid-action button (M1 proof).
