# e042-decide-click-1 — one-click APRUEBO/ESPERAMOS capture live in banco app (2026-09-24)

Dad can now answer the August-close ask with one click — on the PIN screen
(no login needed) or the Inicio tab — instead of replying by WhatsApp.
Clicks append to `runs/e042-decisions.jsonl` (this repo). Zero writes to
`../e042-bk2/banco.db`. Every cell below comes from a command run on
2026-09-24 (`curl` local 9091 + public funnel URL, read-only `SELECT` on the
live DB, `stat`/`md5sum` on `banco.db`). No PIN quoted.

## What changed (2 files, no DB touch)

| fact | value | checked_at |
|---|---|---|
| edited file 1 | ../e042-bk2/app.py (+25 lines: /api/decide endpoint, auth-exempt, append-only JSONL) | 2026-09-24 |
| edited file 2 | ../e042-bk2/static/index.html (+3 blocks: Inicio buttons, PIN-screen buttons, fetch handler) | 2026-09-24 |
| decisions log | runs/e042-decisions.jsonl (0 bytes after test cleanup — no real click yet) | 2026-09-24 |
| app restart | uvicorn 9091 restarted (new pid) so endpoint goes live; funnel survived | 2026-09-24 |

Endpoint design: `POST /api/decide {"decision","source"}` — exempt from the
auth middleware (PIN screen works unauthenticated), validates against
(APRUEBO, ESPERAMOS) else 400, appends `{"ts","decision","source"}` to the
JSONL log. It never calls `db()` — no SQLite connection is even opened.

## Buttons live via curl (one fact per column)

| fact | value | checked_at |
|---|---|---|
| local root | 200, 42517B | 2026-09-24 |
| public root | 200, byte-identical to local | 2026-09-24 |
| data-decide buttons local | 4 (APRUEBO+ESPERAMOS × pin+inicio) | 2026-09-24 |
| data-decide buttons public | 4, same set | 2026-09-24 |
| local /api/report unauth | 401 (gate intact) | 2026-09-24 |
| public /api/report unauth | 401 (gate intact) | 2026-09-24 |

## Test clicks round-tripped then removed (one fact per column)

| fact | value | checked_at |
|---|---|---|
| local test POST | {"decision":"APRUEBO","source":"test-local"} → {"ok":true} | 2026-09-24 |
| public test POST | {"decision":"ESPERAMOS","source":"test-public"} → {"ok":true} | 2026-09-24 |
| bad value POST | {"decision":"SI"} → 400 | 2026-09-24 |
| log before cleanup | 2 test rows present (both verified via cat) | 2026-09-24 |
| log after cleanup | 0 bytes, test rows removed | 2026-09-24 |
| dad reply | PENDING — no real click on record, only removed tests | 2026-09-24 |

## Live DB untouched (one fact per column)

| fact | value | checked_at |
|---|---|---|
| live valorizations | 0 rows | 2026-09-24 |
| banco.db mtime | 2026-08-23 (pre-leg, unchanged) | 2026-09-24 |
| banco.db md5 | ba22f042f4ee2d8c6eef337f5604941d (same before/after) | 2026-09-24 |

Note: first cleanup attempt silently failed (`grep -v` exits 1 when every
line matches, so `&&` skipped the rewrite) — caught on re-read, redone with
`;`, verified 0 bytes. Next leg: poll `runs/e042-decisions.jsonl`; a real
APRUEBO row is the gate to run the live close.
