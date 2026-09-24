# e042-dad-send-1 — One-tap dad approval pack: live 10000.00 vs copy 10003.81 (2026-09-24)

Live `../e042-bk2/banco.db` SELECT-only, zero writes. All writes ran on
`/tmp/e042-dad-send-1.db` + `/tmp/e042-dad-send-1-app/banco.db` (copies only).
Every cell below comes from a command run on 2026-09-24 (`sqlite3` SELECTs,
live HTTP `GET /api/report` + `GET /api/valorizacion/preview?month=2026-08`
against live 9091 and copy 9095, `curl` public URL) or stays empty.
No PIN/token quoted.

## Verdict: forward pack ready, both previews from live HTTP

Before (live 9091): preview `profit 0.0 / delta 0.0 / new_value 10000.0`,
report `action_value 10000.0`, all 38 gains `0.0`, `last_valorization None`.
After (copy 9095, split+close applied): preview `interests_total 64500.0 /
profit 58050.0 / delta 3.81 / new_value 10003.81`, report `action_value
10003.81` with stored `2026-08` valorization row. Public funnel URL 200
(39491B, PIN screen, public `/api/report` 401). Live valorizations still 0
rows, live payments still `61|34446878.12|0.0`. Forward text staged at
`runs/e042-dad-forward-2026-08.txt` (Spanish, one-tap APRUEBO/ESPERAMOS).

## Before: live HTTP (port 9091, member-visible)

| fact | value | checked_at |
|---|---|---|
| live report status | 200 | 2026-09-24 |
| live action_value | 10000.0 | 2026-09-24 |
| live box | -19941004.68 | 2026-09-24 |
| live money_in | 186626878.12 | 2026-09-24 |
| live money_out | 206567882.8 | 2026-09-24 |
| live last_valorization | None | 2026-09-24 |
| live gains | 38 members, all last_gain 0.0 | 2026-09-24 |

| month | interest_ord | interest_pronto | interest_distrib | interests_total | solidarity | fines | expenses | diezmo | profit | total_actions | delta | prev_value | new_value | checked_at |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08 (live preview) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 15218.0 | 0.0 | 10000.0 | 10000.0 | 2026-09-24 |

## Copy build (all writes on /tmp only)

| fact | value | checked_at |
|---|---|---|
| copy path | /tmp/e042-dad-send-1.db (from `cp ../e042-bk2/banco.db`) | 2026-09-24 |
| app copy dir | /tmp/e042-dad-send-1-app (app.py + static + banco.db copy) | 2026-09-24 |
| payments split | 61 / principal 29442533.97 / interest 5004344.15 | 2026-09-24 |
| cash preserved | SUM(principal+interest) 34446878.12 (same as live) | 2026-09-24 |
| 2026-08 pay split | principal 85500.0 + interest 64500.0 = cash 150000.0 | 2026-09-24 |
| valorizations on copy | 1 row: 2026-08 / 64500.0 / 6450.0 / 58050.0 / 15218.0 / 3.81 / 10003.81 | 2026-09-24 |
| copy app port | 9095, root 200 | 2026-09-24 |

## After: copy HTTP (port 9095, member-visible)

| fact | value | checked_at |
|---|---|---|
| copy report status | 200 | 2026-09-24 |
| copy action_value | 10003.81 | 2026-09-24 |
| copy box | -19941004.68 (unchanged, split preserves cash) | 2026-09-24 |
| copy last_valorization | 2026-08 / profit 58050.0 / delta 3.81 / new_value 10003.81 | 2026-09-24 |
| copy gains | 38 members, 36 non-zero, 2 zero-share still 0.0 | 2026-09-24 |

| month | interest_ord | interest_pronto | interest_distrib | interests_total | solidarity | fines | expenses | diezmo | profit | total_actions | delta | prev_value | new_value | checked_at |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08 (copy preview) | 0.0 | 64500.0 | 0.0 | 64500.0 | 0.0 | 0.0 | 0.0 | 6450.0 | 58050.0 | 15218.0 | 3.81 | 10000.0 | 10003.81 | 2026-09-24 |

Copy gain samples (shares × delta 3.81):

| member | total_shares | last_gain | checked_at |
|---|---|---|---|
| AMALFY MOLANO | 184.0 | 701.04 | 2026-09-24 |
| ANGIE NATHALIA GALVIS VIDAL | 252.0 | 960.12 | 2026-09-24 |
| CIELO MARÍA LOPEZ | 170.0 | 647.7 | 2026-09-24 |

## Public funnel (member-visible door)

| fact | value | checked_at |
|---|---|---|
| public root | 200, 39491B | 2026-09-24 |
| public title hits | Banco Comunal x3 | 2026-09-24 |
| public PIN gate refs | password/pin x11 | 2026-09-24 |
| public /api/report unauth | 401 | 2026-09-24 |

## Live DB still untouched (SELECT, this leg)

| fact | value | checked_at |
|---|---|---|
| live valorizations | 0 rows | 2026-09-24 |
| live payments | 61 / principal 34446878.12 / interest 0.0 | 2026-09-24 |
| live members/credits/purchases | 38 / 76 / 721 | 2026-09-24 |
| live solidarity/fines/expenses | 0 / 0 / 0 | 2026-09-24 |

## Evidence ledger (command → fact)

- `sqlite3 banco.db SELECT COUNT(*) FROM valorizations` → 0 (before and after).
- `sqlite3 banco.db SELECT COUNT(*),SUM(principal),SUM(interest) FROM payments` → 61|34446878.12|0.0.
- Live `POST /api/login` + `GET /api/report` (9091) → 200, action_value 10000.0, box -19941004.68, last None, 38 gains 0.0.
- Live `GET /api/valorizacion/preview?month=2026-08` (9091) → 200, 0.0/0.0/10000.0 row above.
- `cp banco.db /tmp/e042-dad-send-1.db` → copy created.
- Split UPDATE on copy → 61|29442533.97|5004344.15, cash 34446878.12; 2026-08 pay 85500.0/64500.0.
- Valorization INSERT on copy → 1 row 2026-08 64500.0/6450.0/58050.0/15218.0/3.81/10003.81.
- Copy app boot (9095) → root 200; authed `/api/report` → 10003.81 + stored row; preview → 64500.0/58050.0/3.81/10003.81; gains samples above.
- Public `curl https://vuos-hcar5000mi.tail6918b0.ts.net/` → 200 39491B; public `/api/report` → 401.
- Copy app stopped after capture; live 9091 left running.
