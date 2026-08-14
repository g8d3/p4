# ag-12 — Session log

## Start
2026-08-14 08:27 UTC (window 25-12)

## Task
Per-quarter stability of volatility, tails, event frequency, weekday effect,
and daily-crash reversion; trend test; report + beginners guide + charts.

## Inputs verified
- `../ag-01-data/output/candles_raw.csv` — 135,232 rows; 12 coins × 4 tfs.
- Dropped 3,175 `v=0` synthetic pre-listing rows (same convention as ag-07) →
  132,057. After drop, only 7 coins (BTC/ETH/SOL/AAVE/CRV/DOGE/XRP) have ≥3y
  of 1d history; HYPE from 2024-12, PUMP/ZEC/LIT/XMR much later.
- Timeframe coverage (post-drop): 5m ~17.5 days, 1h ~7 months, 1d ~3.5y, 1w
  ~190 candles/coin max. 5m not splittable; 1w quarters have only ~13 candles.

## Work done (command count: 8 bash calls, 2 script runs)
1. Read inherited AGENTS.md (fundamentals, ag-02 derived columns, e025 scope).
2. Inspected candles_raw.csv structure, coverage, duplicates, v=0 rows.
3. Read ag-05/ag-06/ag-07 reports to pin down exact pattern definitions:
   - Weekday effect: ag-06 trades same-day intraday (c−o)/o; ag-05 measured
     next-day ret_next. Used the ag-06 (intraday) definition per ag-12 brief,
     cross-checked against ret_next in the report.
   - Crash reversion: 1d down 3σ events, next-5 close-to-close return (ag-07).
4. Wrote `bin/analyze.py`; ran twice after fixing two bugs (below).
5. Verified outputs numerically against ag-05/ag-06/ag-07 headline numbers
   (weekday medians, crash next-5 +2.47/+3.07, event counts) — exact match.
6. Wrote report.md, beginners_guide.md, this log, done.txt.

## Problems hit and how solved
1. **Quarter label zero-stripping bug** — `strftime("%YQ%q")` + `replace("0","")`
   destroyed the "0" in "2023" (→ "223Q"), breaking the qidx parser. Solved by
   building labels from `year + "Q" + quarter` directly.
2. **SeriesGroupBy / Series division bug** — `grp.shift(-5) / grp` divided by
   the groupby object itself (numpy inhomogeneous-shape ValueError). Solved by
   dividing by `sub["c"]` (the plain aligned Series) instead.
3. **KeyError 'qidx' in charts** — quarters.csv lacked the numeric quarter
   index used for sorting; added `qidx` column to the CSV rows.

## Notes / context consumed
- Reading the three previous reports (ag-05/06/07) was necessary to reproduce
  their exact definitions; without it the quarterly numbers could not be
  validated. This is the main context cost of the task.
- Charts rendered with the Agg backend; verified by PNG size/dimensions (this
  model cannot view images, so charts were validated via the underlying
  numbers instead).

## End
2026-08-14 ~08:40 UTC. All deliverables present:
`quarters.csv`, `pattern_stability.csv`, `trend_test.csv`,
`pooled_quarters.csv`, `charts/` (7 PNGs), `report.md`, `beginners_guide.md`,
`done.txt`.

## Headline verdict (for done.txt)
Distribution is NOT stationary: vol regime-cycles 2.0↔6.2% (1d σ), event
frequency varies ~10×, weekday effect flips sign (5/15 quarters match). Stable:
fat tails (kurtosis >3 in all 15 quarters) and crash reversion (8/10 quarters
positive; fails only in down-markets).
