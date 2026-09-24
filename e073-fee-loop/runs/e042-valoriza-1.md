# e042-valoriza-1 — First month-close valorizacion preview (read-only, 2026-09-24)

No closing rows written. `valorizations` still 0 rows. Every cell below comes
from `sqlite3 banco.db` SELECTs + `app.py` preview logic read on 2026-09-24,
or stays empty. No PIN/token quoted.

## Verdict: preview computes to zero — do NOT commit until interest is split

Close candidate **2026-08** (latest activity month, dad's meeting month)
previews to `profit 0.0 / delta 0.0 / new_value 10000.0`. All 38 member gains
are `0.0`. Same zero result for all 10 payment months: every one of the 61
payments carries `interest 0.0` (imported lump sums, interest never split),
and solidarity/fines/expenses tables are all 0 rows. Committing today would
freeze a meaningless `delta 0` row.

## Inputs (verified this leg)

| fact | value | method | checked_at |
|---|---|---|---|
| members | 38 | `SELECT COUNT(*) FROM members` | 2026-09-24 |
| credits | 76 | `SELECT COUNT(*) FROM credits` | 2026-09-24 |
| payments | 61 | `SELECT COUNT(*), SUM(principal), SUM(interest) FROM payments` → principal 34446878.12, interest 0.0 | 2026-09-24 |
| purchases | 721 | `SELECT COUNT(*), SUM(shares), SUM(shares*unit_value) FROM purchases` → shares 15218.0, amount 152180000.0 | 2026-09-24 |
| valorizations | 0 | `SELECT COUNT(*) FROM valorizations` | 2026-09-24 |
| solidarity rows | 0 | `SELECT COUNT(*) FROM solidarity` | 2026-09-24 |
| fines rows | 0 | `SELECT COUNT(*) FROM fines` | 2026-09-24 |
| expenses rows | 0 | `SELECT COUNT(*) FROM expenses` | 2026-09-24 |
| settings | rate 3, diezmo 10, solidaridad 5000, valor_inicial 10000, term_distrib 18 | `SELECT key,value FROM settings` | 2026-09-24 |
| interest by kind | distribucion 35 / 20756944.25 / 0.0; ordinario 17 / 7239933.87 / 0.0; pronto 9 / 6450000.0 / 0.0 | `JOIN credits GROUP BY kind` | 2026-09-24 |

## Close-candidate preview: 2026-08 (one fact per column)

Logic: `app.py` `MonthTotals.compute` — interests (month payments) + solidarity + fines − diezmo (10% of interests) − expenses = profit; `total_actions` = SUM(shares) WHERE date < 'month-99'; `delta` = profit / total_actions; `new_value` = prev_value + delta; prev_value = last `new_value` or `valor_inicial` (no rows → 10000).

| month | interest_ord | interest_pronto | interest_distrib | interests_total | solidarity | fines | expenses | diezmo | profit | total_actions | delta | prev_value | new_value | checked_at |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 15218.0 | 0.0 | 10000.0 | 10000.0 | 2026-09-24 |

Month payments behind it: 2026-08 has 1 payment (principal 150000.0, interest 0.0).

## All payment months preview to the same zero (why: interest 0.0 every month)

| month | payments | principal | interest | total_actions | profit | delta | checked_at |
|---|---|---|---|---|---|---|---|
| 2025-11 | 2 | 4700000.0 | 0.0 | 6953.0 | 0.0 | 0.0 | 2026-09-24 |
| 2025-12 | 1 | 100000.0 | 0.0 | 7841.0 | 0.0 | 0.0 | 2026-09-24 |
| 2026-01 | 2 | 1210000.0 | 0.0 | 8685.0 | 0.0 | 0.0 | 2026-09-24 |
| 2026-02 | 36 | 21801877.58 | 0.0 | 9605.0 | 0.0 | 0.0 | 2026-09-24 |
| 2026-03 | 1 | 666666.67 | 0.0 | 10532.0 | 0.0 | 0.0 | 2026-09-24 |
| 2026-04 | 3 | 1100000.0 | 0.0 | 11490.0 | 0.0 | 0.0 | 2026-09-24 |
| 2026-05 | 2 | 1525000.0 | 0.0 | 12416.0 | 0.0 | 0.0 | 2026-09-24 |
| 2026-06 | 1 | 280000.0 | 0.0 | 13333.0 | 0.0 | 0.0 | 2026-09-24 |
| 2026-07 | 12 | 2913333.87 | 0.0 | 14175.0 | 0.0 | 0.0 | 2026-09-24 |
| 2026-08 | 1 | 150000.0 | 0.0 | 15218.0 | 0.0 | 0.0 | 2026-09-24 |

## Per-member preview for 2026-08 (gain = shares × delta 0.0)

Full set computed: 38 members, every `last_gain 0.0`. Largest holders shown + zero-share edge cases; full list verifiable by one query (see evidence).

| member | total_shares | last_delta | last_gain | checked_at |
|---|---|---|---|---|
| MARTHA OFELIA CERÓN MUÑOZ | 1800.0 | 0.0 | 0.0 | 2026-09-24 |
| MARIA CAMILA PASTAS LLANOS | 1478.0 | 0.0 | 0.0 | 2026-09-24 |
| JUAN FELIPE ALEGRIA MESA | 1351.0 | 0.0 | 0.0 | 2026-09-24 |
| LUZ FANY VIDAL MENDEZ | 1320.0 | 0.0 | 0.0 | 2026-09-24 |
| SAUL MARINO PASTAS LLANOS | 1246.0 | 0.0 | 0.0 | 2026-09-24 |
| JENNIFER ALEXANDRA PINEDA QUILINDO | 905.0 | 0.0 | 0.0 | 2026-09-24 |
| DIANA GABRIELA VIDAL MENDEZ | 730.0 | 0.0 | 0.0 | 2026-09-24 |
| DANIELA PASTAS RIVERA | 504.0 | 0.0 | 0.0 | 2026-09-24 |
| HERMES ASTUDILLO SANDOVAL | 0.0 | 0.0 | 0.0 | 2026-09-24 |
| MONICA DEL PILAR TORRES | 0.0 | 0.0 | 0.0 | 2026-09-24 |

Remaining 28 members: shares 121.0–455.0 each (see db), all `last_gain 0.0`, 2026-09-24.

## The one commit that would close the month (NOT run)

Endpoint (idempotent per month, `ON CONFLICT(month) DO UPDATE`):

```
POST /api/valorizacion  {"month": "2026-08", "note": ""}
```

It executes this single SQL (app.py `save_valorization`, values = preview row above):

```sql
INSERT INTO valorizations
  (month, interest_ord, interest_pronto, interest_distrib, solidarity, fines,
   expenses_total, diezmo, profit, total_actions, delta, new_value, note)
VALUES ('2026-08', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 15218.0, 0.0, 10000.0, '')
ON CONFLICT(month) DO UPDATE SET
  interest_ord=excluded.interest_ord, interest_pronto=excluded.interest_pronto,
  interest_distrib=excluded.interest_distrib, solidarity=excluded.solidarity,
  fines=excluded.fines, expenses_total=excluded.expenses_total,
  diezmo=excluded.diezmo, profit=excluded.profit, total_actions=excluded.total_actions,
  delta=excluded.delta, new_value=excluded.new_value, note=excluded.note;
```

Preview without committing (safe, read-only):

```
GET /api/valorizacion/preview?month=2026-08
```

## Single next action for a non-zero close

Split each payment's `principal`/`interest` (3% rule on outstanding balance per `AGENTS.md` model) and record monthly solidarity/fines/expenses; then re-run preview — only commit when `interests_total > 0`.

## Evidence ledger (command → fact)

- `SELECT COUNT(*), SUM(principal), SUM(interest) FROM payments` → 61 / 34446878.12 / 0.0.
- `SELECT substr(date,1,7), COUNT(*), SUM(principal), SUM(interest) FROM payments GROUP BY 1` → 10-month table above.
- `SELECT COUNT(*), SUM(shares), SUM(shares*unit_value) FROM purchases` → 721 / 15218.0 / 152180000.0.
- `SELECT ... SUM(shares) WHERE date < month||'-99'` → actions_until column above (2026-08: 15218.0).
- `SELECT COUNT(*) FROM valorizations/solidarity/fines/expenses` → 0 / 0 / 0 / 0.
- `JOIN credits GROUP BY kind` → 35/17/9 split with 0.0 interest each.
- `members LEFT JOIN purchases GROUP BY member` → 38 share balances (top/bottom above).
- `app.py` lines 596–673 read: `compute` + `save_valorization` SQL quoted above; no INSERT executed this leg.
