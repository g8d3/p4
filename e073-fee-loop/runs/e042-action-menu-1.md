# e042-action-menu-1 — paid-action menu NOT BUILT, docs-only leg (2026-09-24)

Status: NOT DONE. No paid-action menu exists in the live app. This leg was
restricted to writing this proof file + one PROGRESS.md leg-log line, so no
code was changed (`../e042-bk2/app.py` and `../e042-bk2/static/index.html`
untouched by this leg). Every cell below comes from a command run on
2026-09-24 (`curl` local 9091 + public funnel URL, `grep`/`cmp`/`md5sum` on
fetched roots, read-only `SELECT count(*)` on the live DB, `stat`/`md5sum`
on `banco.db`). No PIN quoted.

## Menu markers absent via curl (one fact per column)

| fact | value | checked_at |
|---|---|---|
| local root | 200, 44940B | 2026-09-24 |
| public root | 200, 44940B | 2026-09-24 |
| local vs public roots | byte-identical (cmp identical, md5 b3a272b434807c4d03fc20ca5688f1df both) | 2026-09-24 |
| menu markers local | 0 (grep api/action\|action-menu\|data-action\|form-action → no hits) | 2026-09-24 |
| menu markers public | 0 (same grep → no hits) | 2026-09-24 |
| priced paid actions live | 0 (no menu block in either root) | 2026-09-24 |

## Action endpoint absent (one fact per column)

| fact | value | checked_at |
|---|---|---|
| local POST /api/action | 401 {"detail":"auth"} (no exempt endpoint; auth middleware gate) | 2026-09-24 |
| public POST /api/actions | 401 {"detail":"auth"} (no exempt endpoint) | 2026-09-24 |
| test requests round-tripped | 0 — not performed, no endpoint to hit | 2026-09-24 |
| runs/e042-actions.jsonl | absent (no such file, 0 rows, nothing to clean) | 2026-09-24 |
| real action requests | PENDING — no menu, no log, no stranger row | 2026-09-24 |

## Gates + live DB untouched (one fact per column)

| fact | value | checked_at |
|---|---|---|
| local /api/report unauth | 401 (gate intact) | 2026-09-24 |
| public /api/report unauth | 401 (gate intact) | 2026-09-24 |
| live valorizations | 0 rows | 2026-09-24 |
| banco.db mtime | 2026-08-23 (pre-leg, unchanged) | 2026-09-24 |
| banco.db md5 | ba22f042f4ee2d8c6eef337f5604941d (same before/after) | 2026-09-24 |

Next leg (builder, needs app.py + index.html write): add 1–3 priced paid
actions with one-click buttons POSTing to an auth-exempt append-only
`/api/action` → `runs/e042-actions.jsonl` (same pattern as `/api/refer`),
surface the menu on the PIN screen + Inicio with no login, reboot 9091,
re-verify local+public 200 with markers, round-trip test requests local +
public then remove (0 real rows), keep /api/report 401 both doors and
banco.db mtime+md5 unchanged with valorizations 0 rows.
