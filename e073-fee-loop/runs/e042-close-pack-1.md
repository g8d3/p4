# e042-close-pack-1 — Close pack on /tmp copy: split applied, 2026-08 verified, live-run staged (2026-09-24)

Live `../e042-bk2/banco.db` untouched. All writes ran on `/tmp/e042-close-pack-1.db`
(copy only). Live valorizations still 0 rows (SELECT-confirmed). No valorizacion
committed anywhere. Every cell below comes from `sqlite3` SELECTs on the copy/live
DBs plus `app.py` model code read on 2026-09-24, or stays empty. No PIN quoted.

## Verdict: copy-DB split verifies the interest-split-1 numbers exactly

Applied 3%-on-balance principal/interest split UPDATEs to the copy (61/61 rows),
recomputed 2026-08 preview from stored copy data: `interests_total 64500.0 /
diezmo 6450.0 / profit 58050.0 / delta 3.81 / new_value 10003.81` on 15218 shares —
matches `runs/e042-interest-split-1.md` exactly. Staged SQL + owner-forward text
below wait for dad approve/deny. Nothing to commit until he approves.

## What ran on the copy (one fact per column)

| fact | value | checked_at |
|---|---|---|
| copy path | /tmp/e042-close-pack-1.db (from `cp ../e042-bk2/banco.db`) | 2026-09-24 |
| payments updated | 61 / 61 | 2026-09-24 |
| copy cash preserved | SUM(principal+interest) 34446878.12 (same as live before split) | 2026-09-24 |
| copy SUM(principal) | 29442533.97 | 2026-09-24 |
| copy SUM(interest) | 5004344.15 (= capped total from interest-split-1: due 5069244.15 − 64900 over 3 short-cash pays) | 2026-09-24 |
| copy valorizations | 0 rows (no commit on copy either) | 2026-09-24 |
| SQL-vs-python agreement | 0 mismatches over 61 rows (SQL `ROUND(x+1e-9,2)` == app.py `round2`) | 2026-09-24 |
| idempotency | UPDATE re-run on copy → same 29442533.97 / 5004344.15 | 2026-09-24 |

## Copy per-month interest after split (matches interest-split-1 capped column)

| month | n_payments | cash_total | interest | checked_at |
|---|---|---|---|---|
| 2025-11 | 2 | 4700000.0 | 420000.0 | 2026-09-24 |
| 2025-12 | 1 | 100000.0 | 100000.0 | 2026-09-24 |
| 2026-01 | 2 | 1210000.0 | 91800.0 | 2026-09-24 |
| 2026-02 | 36 | 21801877.58 | 2335794.0 | 2026-09-24 |
| 2026-03 | 1 | 666666.67 | 24000.0 | 2026-09-24 |
| 2026-04 | 3 | 1100000.0 | 100500.0 | 2026-09-24 |
| 2026-05 | 2 | 1525000.0 | 219000.0 | 2026-09-24 |
| 2026-06 | 1 | 280000.0 | 42000.0 | 2026-09-24 |
| 2026-07 | 12 | 2913333.87 | 1606750.15 | 2026-09-24 |
| 2026-08 | 1 | 150000.0 | 64500.0 | 2026-09-24 |

## Copy 2026-08 preview recomputed from stored data (first-close basis)

Logic: `app.py` `MonthTotals.compute` — interests (stored `payments.interest` in
month) + solidarity + fines − diezmo (10% of interests) − expenses = profit;
`total_actions` = SUM(shares) WHERE date < 'month-99'; `delta` = profit /
total_actions; `new_value` = prev_value + delta; prev_value = last `new_value`
or `valor_inicial` (copy valorizations 0 rows → 10000).

| month | interest_ord | interest_pronto | interest_distrib | interests_total | solidarity | fines | expenses | diezmo | profit | total_actions | delta | prev_value | new_value | checked_at |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08 | 0.0 | 64500.0 | 0.0 | 64500.0 | 0.0 | 0.0 | 0.0 | 6450.0 | 58050.0 | 15218.0 | 3.81 | 10000.0 | 10003.81 | 2026-09-24 |

Source payment on copy: pay 20 → pronto, principal 85500.0 + interest 64500.0 =
cash 150000.0 (was: principal 150000.0 + interest 0.0 on live).

## Edge rows where cash < due (principal 0, all-cash-to-interest, 3 rows)

| pay_id | month | principal | interest | checked_at |
|---|---|---|---|---|
| 23 | 2025-12 | 0.0 | 100000.0 | 2026-09-24 |
| 1 | 2026-07 | 0.0 | 350694.44 | 2026-09-24 |
| 5 | 2026-07 | 0.0 | 405555.56 | 2026-09-24 |

## Staged live-run SQL (NOT run — waits for dad approval)

Step 1 — split (exact, idempotent, single statement; rerun-safe because every
RHS reads pre-update values and cash = principal+interest is preserved):

```sql
UPDATE payments AS p SET
  interest = MIN(p.principal + p.interest, ROUND(c.amount * c.rate_pct / 100.0 + 0.000000001, 2)),
  principal = (p.principal + p.interest) - MIN(p.principal + p.interest, ROUND(c.amount * c.rate_pct / 100.0 + 0.000000001, 2))
FROM credits AS c WHERE c.id = p.credit_id;
```

Step 2 — verify before any commit (must print `61|29442533.97|5004344.15`):

```sql
SELECT COUNT(*), SUM(principal), SUM(interest) FROM payments;
```

Step 3 — re-run preview, commit only when `interests_total > 0` from stored data:

```
GET /api/valorizacion/preview?month=2026-08
```

Step 4 — close 2026-08 (values = verified copy preview above; same idempotent
`ON CONFLICT` form as `app.py` `save_valorization`):

```sql
INSERT INTO valorizations
  (month, interest_ord, interest_pronto, interest_distrib, solidarity, fines,
   expenses_total, diezmo, profit, total_actions, delta, new_value, note)
VALUES ('2026-08', 0.0, 64500.0, 0.0, 0.0, 0.0, 0.0, 6450.0, 58050.0, 15218.0, 3.81, 10003.81, '')
ON CONFLICT(month) DO UPDATE SET
  interest_ord=excluded.interest_ord, interest_pronto=excluded.interest_pronto,
  interest_distrib=excluded.interest_distrib, solidarity=excluded.solidarity,
  fines=excluded.fines, expenses_total=excluded.expenses_total,
  diezmo=excluded.diezmo, profit=excluded.profit, total_actions=excluded.total_actions,
  delta=excluded.delta, new_value=excluded.new_value, note=excluded.note;
```

Rollback note: the split is reversible before step 4 — `principal = principal +
interest, interest = 0` restores the imported lump sums exactly (cash preserved).
After step 4, re-running the preview must still print the same row.

## Owner-forward text (Spanish, 5 lines, for dad approve/deny)

> Agosto cierra con interés 64500, ganancia 58050 y acción a 10003.81, verificado en copia.
> En vivo no se tocó nada: valorizaciones siguen en 0 y los 61 pagos siguen en 0 interés.
> Para cerrar en vivo hay que dividir cada pago en capital/interés al 3% y guardar el mes.
> Si aprueba, corremos el SQL ya probado y le mostramos el antes/después.
> Si no aprueba, la copia se borra y todo queda como está. ¿Aprobamos o esperamos?

## Live DB confirmed still 0 valorizations (SELECT, this leg)

| fact | value | checked_at |
|---|---|---|
| live valorizations | 0 rows | 2026-09-24 |
| live payments | 61 / principal 34446878.12 / interest 0.0 (split NOT applied) | 2026-09-24 |

## Evidence ledger (command → fact)

- `cp ../e042-bk2/banco.db /tmp/e042-close-pack-1.db` → copy created.
- Staged split UPDATE on copy → `61|29442533.97|5004344.15`, cash 34446878.12 preserved.
- `... GROUP BY substr(p.date,1,7)` on copy → 10-month table above (== interest-split-1 capped).
- Python `round2` recompute of `MonthTotals` on copy → 64500.0/6450.0/58050.0/15218.0/3.81/10003.81.
- 61-row python-vs-SQL comparison → 0 mismatches.
- UPDATE re-run on copy → identical sums (idempotent).
- `SELECT COUNT(*) FROM valorizations` on live → 0; `SUM(principal/interest)` on live → 34446878.12/0.0.
- `SELECT key,value FROM settings` read for rate/diezmo/valor_inicial (values used above; PIN never quoted).
