# e042-interest-split-1 — Per-payment interest recompute (read-only, 2026-09-24)

No DB writes. `valorizations` still 0 rows. No valorizacion committed. No PIN quoted.
Every cell below comes from `sqlite3 banco.db` SELECTs + `app.py` model code read on
2026-09-24, or stays empty.

## Verdict: 2026-08 previews non-zero once interest is split

Recomputed 2026-08: `interests_total 64500.0 / diezmo 6450.0 / profit 58050.0 /
delta 3.81 / new_value 10003.81` (first-close basis, prev_value 10000.0).
All 10 payment months show recomputed interest > 0. The stored payments still carry
`interest 0.0` (61/61 imported lump sums) — committing today still freezes a zero row;
split first, then re-run preview, then commit.

## Method (e042-bk2 AGENTS model, read from app.py)

- `credit_status`: `interest_due = balance * rate_pct / 100` (3%), `principal_paid =
  SUM(p.principal)`, `balance = amount - principal_paid`.
- Verified precondition: every credit in `banco.db` has exactly one payment
  (`GROUP BY credit_id HAVING COUNT(*)>1` → 0 rows), so outstanding balance before
  each payment = full `credits.amount`, and `interest_due = amount * 3%`.
- Two interest columns, one fact each:
  - `interest_due` = model interest owed (balance × rate, uncapped).
  - `interest_capped` = cash-consistent collectible part = `MIN(cash_total, interest_due)`
    (what a principal/interest split of the recorded cash could actually book).
- They differ in only 3 of 61 payments (due > cash: pay 23, pay 1, pay 5); for 2026-08
  they coincide (cash 150000.0 ≥ due 64500.0), so the preview below is unambiguous.

## Per-month recomputed interest (10 payment months, one fact per column)

Monthly totals:

| month | n_payments | cash_total | interest_due | interest_capped | checked_at |
|---|---|---|---|---|---|
| 2025-11 | 2 | 4700000.0 | 420000.0 | 420000.0 | 2026-09-24 |
| 2025-12 | 1 | 100000.0 | 104400.0 | 100000.0 | 2026-09-24 |
| 2026-01 | 2 | 1210000.0 | 91800.0 | 91800.0 | 2026-09-24 |
| 2026-02 | 36 | 21801877.58 | 2335794.0 | 2335794.0 | 2026-09-24 |
| 2026-03 | 1 | 666666.67 | 24000.0 | 24000.0 | 2026-09-24 |
| 2026-04 | 3 | 1100000.0 | 100500.0 | 100500.0 | 2026-09-24 |
| 2026-05 | 2 | 1525000.0 | 219000.0 | 219000.0 | 2026-09-24 |
| 2026-06 | 1 | 280000.0 | 42000.0 | 42000.0 | 2026-09-24 |
| 2026-07 | 12 | 2913333.87 | 1667250.15 | 1606750.15 | 2026-09-24 |
| 2026-08 | 1 | 150000.0 | 64500.0 | 64500.0 | 2026-09-24 |

Split by kind (valorizacion income buckets):

| month | kind | n_payments | cash_total | interest_due | interest_capped | checked_at |
|---|---|---|---|---|---|---|
| 2025-11 | pronto | 2 | 4700000.0 | 420000.0 | 420000.0 | 2026-09-24 |
| 2025-12 | pronto | 1 | 100000.0 | 104400.0 | 100000.0 | 2026-09-24 |
| 2026-01 | ordinario | 1 | 910000.0 | 31800.0 | 31800.0 | 2026-09-24 |
| 2026-01 | pronto | 1 | 300000.0 | 60000.0 | 60000.0 | 2026-09-24 |
| 2026-02 | ordinario | 1 | 1044933.33 | 94044.0 | 94044.0 | 2026-09-24 |
| 2026-02 | distribucion | 35 | 20756944.25 | 2241750.0 | 2241750.0 | 2026-09-24 |
| 2026-03 | ordinario | 1 | 666666.67 | 24000.0 | 24000.0 | 2026-09-24 |
| 2026-04 | pronto | 3 | 1100000.0 | 100500.0 | 100500.0 | 2026-09-24 |
| 2026-05 | ordinario | 2 | 1525000.0 | 219000.0 | 219000.0 | 2026-09-24 |
| 2026-06 | ordinario | 1 | 280000.0 | 42000.0 | 42000.0 | 2026-09-24 |
| 2026-07 | ordinario | 11 | 2813333.87 | 1607250.15 | 1546750.15 | 2026-09-24 |
| 2026-07 | pronto | 1 | 100000.0 | 60000.0 | 60000.0 | 2026-09-24 |
| 2026-08 | pronto | 1 | 150000.0 | 64500.0 | 64500.0 | 2026-09-24 |

The 3 due>cash payments (why capped < due in 2025-12 and 2026-07):

| pay_id | credit_id | kind | pay_date | cash_total | interest_due | interest_capped | checked_at |
|---|---|---|---|---|---|---|---|
| 23 | 28 | pronto | 2025-12-06 | 100000.0 | 104400.0 | 100000.0 | 2026-09-24 |
| 1 | 1 | ordinario | 2026-07-10 | 350694.44 | 378750.0 | 350694.44 | 2026-09-24 |
| 5 | 6 | ordinario | 2026-07-10 | 405555.56 | 438000.0 | 405555.56 | 2026-09-24 |

All other 58 payments: cash ≥ due, so due == capped.

## 2026-08 preview math (recomputed, first-close basis, one fact per column)

Logic: `app.py` `MonthTotals.compute` — interests (month payments) + solidarity +
fines − diezmo (10% of interests) − expenses = profit; `total_actions` = SUM(shares)
WHERE date < 'month-99'; `delta` = profit / total_actions; `new_value` = prev_value +
delta; prev_value = last `new_value` or `valor_inicial` (no rows → 10000).

Source payment: pay 20 → credit 23 (pronto, MARIELA VIDAL MENDEZ), amount 2150000.0 ×
3% = 64500.0; cash 150000.0 covers it, so split = interest 64500.0 + principal 85500.0.

| month | interest_ord | interest_pronto | interest_distrib | interests_total | solidarity | fines | expenses | diezmo | profit | total_actions | delta | prev_value | new_value | checked_at |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08 | 0.0 | 64500.0 | 0.0 | 64500.0 | 0.0 | 0.0 | 0.0 | 6450.0 | 58050.0 | 15218.0 | 3.81 | 10000.0 | 10003.81 | 2026-09-24 |

Inputs shown: interests 64500.0 > 0; diezmo = 64500.0 × 10% = 6450.0; profit =
64500.0 − 6450.0 = 58050.0 > 0; delta = 58050.0 / 15218.0 = 3.81; new_value =
10000.0 + 3.81 = 10003.81 > 0. `round2` = `round(x + 1e-9, 2)` (app.py line 198).
Chained note: this is the first-close basis (valorizations 0 rows); a real chained
close after prior months would stack earlier deltas onto prev_value, only larger.

## What still blocks a commit

Stored payments still read `interest 0.0` (verified: `SUM(interest)` = 0.0 over 61
rows). The recompute above is SELECT-only. To close: UPDATE each payment's
principal/interest split (or book interest on top — owner decision), record monthly
solidarity/fines/expenses (all 0 rows today), re-run `GET
/api/valorizacion/preview?month=2026-08`, commit only when `interests_total > 0`
from stored data.

## Evidence ledger (command → fact)

- `SELECT credit_id, COUNT(*) FROM payments GROUP BY credit_id HAVING COUNT(*)>1` →
  0 rows (each credit paid once; balance_before = amount).
- `SELECT p.id, p.credit_id, c.kind, p.date, c.amount, c.rate_pct,
  (c.amount*c.rate_pct/100.0), p.principal FROM payments p JOIN credits c ON
  c.id=p.credit_id ORDER BY p.date, p.id` → 61-row per-payment table (due column above).
- `... GROUP BY substr(p.date,1,7)` → 10-month totals table above.
- `... GROUP BY substr(p.date,1,7), c.kind` → 13-row kind-split table above.
- `SELECT COUNT(*), SUM(principal), SUM(interest) FROM payments` → 61 / 34446878.12 / 0.0
  (stored interest still zero — recompute not written).
- `SELECT COALESCE(SUM(shares),0) FROM purchases WHERE date < '2026-08-99'` → 15218.0.
- `SELECT COUNT(*) FROM solidarity/fines/expenses/valorizations` → 0 / 0 / 0 / 0.
- `SELECT key,value FROM settings` → rate_pct 3, diezmo_pct 10, valor_inicial 10000.
- `app.py` lines 198 (round2), 218–250 (credit_status interest_due), 583–646 (MonthTotals
  + preview) read; no INSERT/UPDATE executed this leg. (PIN value present in settings
  read but never quoted here.)
