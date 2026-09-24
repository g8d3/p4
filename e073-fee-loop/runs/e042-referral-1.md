# e042-referral-1 — minimal M1 referral hook live in banco app (2026-09-24)

Strangers can now leave their name with one click — in the PIN screen (no
login needed) or the Inicio tab — instead of needing a member account.
Referrals append to `runs/e042-referrals.jsonl` (this repo). Zero writes to
`../e042-bk2/banco.db`. Every cell below comes from a command run on
2026-09-24 (`curl` local 9091 + public funnel URL, read-only `SELECT` on the
live DB, `stat`/`md5sum` on `banco.db`). No PIN quoted.

## What changed (2 files, no DB touch)

| fact | value | checked_at |
|---|---|---|
| edited file 1 | ../e042-bk2/app.py (+28 lines: /api/refer endpoint, auth-exempt, append-only JSONL) | 2026-09-24 |
| edited file 2 | ../e042-bk2/static/index.html (+3 blocks: Inicio refer card, PIN-screen refer form, postRefer handler) | 2026-09-24 |
| referrals log | runs/e042-referrals.jsonl (0 bytes after test cleanup — no real referral yet) | 2026-09-24 |
| app restart | uvicorn 9091 restarted (new pid) so endpoint goes live; funnel survived | 2026-09-24 |

Endpoint design: `POST /api/refer {"name","contact","source"}` — exempt from
the auth middleware (strangers have no PIN), `name` required non-empty else
400 (lengths capped at 80/80/32 chars), appends
`{"ts","name","contact","source"}` to the JSONL log. It never calls `db()` —
no SQLite connection is even opened.

## Referral block live via curl (one fact per column)

| fact | value | checked_at |
|---|---|---|
| local root | 200, 44940B | 2026-09-24 |
| public root | 200, byte-identical to local | 2026-09-24 |
| refer markers local | form-refer ×4, form-refer-pin ×2, refer-card ×1, /api/refer ×1 | 2026-09-24 |
| refer markers public | same counts as local | 2026-09-24 |
| local /api/report unauth | 401 (gate intact) | 2026-09-24 |
| public /api/report unauth | 401 (gate intact) | 2026-09-24 |

## Test referrals round-tripped then removed (one fact per column)

| fact | value | checked_at |
|---|---|---|
| local test POST | {"name":"Test Vecino","contact":"3001234567","source":"test-local"} → {"ok":true} | 2026-09-24 |
| public test POST | {"name":"Test Vecina","source":"test-public"} → {"ok":true} | 2026-09-24 |
| bad value POST | {"name":"  "} → 400 {"detail":"name is required"} | 2026-09-24 |
| log before cleanup | 2 test rows present (both verified via cat) | 2026-09-24 |
| log after cleanup | 0 bytes, test rows removed | 2026-09-24 |
| real referrals | PENDING — no real referral on record, only removed tests | 2026-09-24 |

## Live DB untouched (one fact per column)

| fact | value | checked_at |
|---|---|---|
| live valorizations | 0 rows | 2026-09-24 |
| banco.db mtime | 2026-08-23 (pre-leg, unchanged) | 2026-09-24 |
| banco.db md5 | ba22f042f4ee2d8c6eef337f5604941d (same before/after) | 2026-09-24 |

Next leg: poll `runs/e042-referrals.jsonl`; a real stranger row is the first
M1 stranger-count movement.
