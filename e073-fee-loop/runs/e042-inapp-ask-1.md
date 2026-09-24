# e042-inapp-ask-1 — August-close approval ask live inside the banco app (2026-09-24)

Read-only notice published on the PIN screen + Inicio tab of the live app so
dad sees the ask without an owner WhatsApp forward. Zero writes to
`../e042-bk2/banco.db` (no valorizacion POST, no payments UPDATE — this leg
ran only GETs + read-only `sqlite3`). Every cell below comes from a command
run on 2026-09-24 (`curl` local 9091 + public funnel URL, read-only `SELECT`
on the live DB) or from the staged forward text
`runs/e042-dad-forward-2026-08.txt` (after-numbers source, per task). No PIN quoted.

## What changed (static HTML only, no JS writes)

| fact | value | checked_at |
|---|---|---|
| edited file | ../e042-bk2/static/index.html (2 static blocks, 0 JS, 0 POST) | 2026-09-24 |
| PIN-screen block | div#ask-ago-pin (before vs after + APRUEBO/ESPERAMOS) | 2026-09-24 |
| Inicio-tab block | div.card#ask-ago (before/after table + examples + APRUEBO/ESPERAMOS) | 2026-09-24 |
| after-numbers source | runs/e042-dad-forward-2026-08.txt | 2026-09-24 |

Notice text (Spanish, read-only): before = acción 10000.00, ganancia agosto 0,
valorizaciones 0 filas; after (copia verificada) = interés 64500, diezmo 6450,
ganancia 58050, acción 10003.81 sobre 15218 acciones (184 → 701.04, 252 → 960.12).
Reply line: responda al dueño APRUEBO (aplicamos el cierre) o ESPERAMOS (todo queda igual).

## Notice visible via curl (one fact per column)

| fact | value | checked_at |
|---|---|---|
| local root | 200, 41302B | 2026-09-24 |
| public root | 200, 41302B, byte-identical to local | 2026-09-24 |
| ask-ago-pin hits | 1 local / 1 public | 2026-09-24 |
| id=ask-ago hits | 1 local / 1 public | 2026-09-24 |
| 10003.81 hits | 2 local / 2 public | 2026-09-24 |
| 58050 hits | 2 local / 2 public | 2026-09-24 |
| APRUEBO hits | 2 local / 2 public | 2026-09-24 |
| ESPERAMOS hits | 2 local / 2 public | 2026-09-24 |

## Live DB untouched (one fact per column)

| fact | value | checked_at |
|---|---|---|
| live valorizations | 0 rows | 2026-09-24 |
| live valor_inicial | 10000 (= action_value 10000.0 with 0 valorizations) | 2026-09-24 |
| banco.db mtime | 2026-08-23 (pre-leg, no write by this leg) | 2026-09-24 |
| valorizacion POSTs | 0 | 2026-09-24 |
| payments UPDATEs | 0 | 2026-09-24 |
| local /api/report unauth | 401 | 2026-09-24 |
| public /api/report unauth | 401 | 2026-09-24 |

Note: authed `/api/report` was not re-hit (access PIN is owner-held; default
no longer applies). action_value 10000.0 is derived read-only: valor_inicial
10000 + 0 valorization rows ⇒ no delta applied. Unauth 401 on both doors
confirms the gate — and the notice itself — is intact.

## Evidence ledger (command → fact)

- `curl http://127.0.0.1:9091/` → 200 41302B; grep ask-ago-pin 1, id=ask-ago 1, 10003.81 x2, 58050 x2, APRUEBO x2, ESPERAMOS x2, 10000.00 x2.
- `curl https://vuos-hcar5000mi.tail6918b0.ts.net/` → 200 41302B, byte-identical to local, same grep hits.
- `curl /api/report` local + public (no cookie) → 401 + 401.
- `sqlite3 "file:../e042-bk2/banco.db?mode=ro" "SELECT count(*) FROM valorizations;"` → 0.
- `sqlite3 (ro) "SELECT value FROM settings WHERE key='valor_inicial';"` → 10000.
- After-numbers (64500/6450/58050/10003.81/15218/701.04/960.12) → quoted from runs/e042-dad-forward-2026-08.txt, not recomputed here.
