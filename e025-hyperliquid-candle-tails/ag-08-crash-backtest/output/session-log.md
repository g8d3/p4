# session-log — ag-08 crash backtest

## Start

2026-08-14 ~08:26 UTC (opencode, opencode-go/deepseek-v4-flash, window 25-8)

## Pre-declared test grid (declared before computing, per e025 rules)

- **Rule A**: enter at close of a 1d crash candle (`ret < −3σ`), hold **5**
  daily candles, exit at close. No leverage, equal notional, no re-entry while
  a position is open.
- **Rule B** (control): same but for rallies (`ret > +3σ`).
- **Rule C** (baseline): long every day (buy close, sell next close).
- **Sensitivity**: Rule A holds 3 and 10 days (report, don't optimize).
- **OOS discipline**: σ computed on the FIRST HALF of each coin's 1d series
  only; events detected only in the SECOND HALF (walk-forward).
- **Fees**: taker 0.045% each side (0.09% round trip), maker 0.018% each side.
  Net applied multiplicatively: `(1+gross)×(1−fee)²−1`.
- **Metrics**: total return, expectancy, win rate, max drawdown, Sharpe-style
  (annualized daily), gross AND net, per-coin + market-pooled (equal weight
  per day). Downgrade conclusion if OOS trades < 30.
- P&L definition: `(close[t+H] − close[t]) / close[t]`; crash candle's own
  return NOT part of the trade.

## Commands run

1. `ls` of agent dir + `../ag-01-data/output/` and `../ag-07-event-study/output/`.
2. Read manifest.json — 12 coins, 4 tfs, per-pair row counts and v=0 counts.
3. Python inline: 1d-only row counts per coin after dropping v=0 (10,262 real
   daily candles), zero duplicate `(coin,tf,t_ms)`, zero gaps in t_ms.
4. Python inline: read ag-07 events.csv + event_paths.csv to confirm the
   finding's definition (cum5 = 5-day cum from event close) — matched.
5. Wrote `bin/backtest.py` (per-coin trade generation: walk-forward σ,
   Rules A/B/C, single-position rule, hold sensitivity, fee variants).
6. First run FAILED on read: I had written the σ/event code but forgot to
   compute the `ret` column (the CSV has no derived columns). Fixed by adding
   `g["ret"] = g["c"].pct_change()*100` in main().
7. Re-ran — SUCCESS: 28 (A), 34 (B), 5,123 (C) trades written to
   `output/backtest.csv` + `output/oos_windows.csv`.
8. Wrote `bin/metrics.py`. First run FAILED: `TypeError: '>=' not supported
   between instances of 'Timestamp' and 'float'` — I had used
   `Series.apply(lambda day: ...)` on a Series of VALUES (NaNs), but the
   lambda expected index timestamps. Fixed by computing `n_alive` once with a
   list comprehension over `all_days` (the index), not `.apply` over values.
9. Second run of metrics FAILED: `KeyError: ('A', 5)` — RULE_LABEL keys used
   `("down",5)` but the loop iterated over `("A",5)`. Unified all keys to
   `("A"|"B"|"C", hold)`.
10. Third run — SUCCESS. Sanity-checked: Rule A n=28, expectancy +1.24% net.
11. Investigated a suspicious Rule C gross total (−42%): independent ad-hoc
    reconstruction of the pooled series reproduced −42.22% EXACTLY, confirming
    the pooled computation; an earlier hand-check (−39%) differed only because
    it credited a return on the first OOS day before any position could be
    open. Confirmed the OOS window was a bear market (BTC 92k→63k, SOL 257→76)
    → explains why always-long lost so much, making Rule A's positive result
    meaningful.
12. Verified per-coin same-sign replication: 7/8 traded coins positive for
    Rule A net; 0/10 for Rule B. Collapsed the 28 A-trades to their 8 distinct
    entry dates to quantify the correlation caveat.
13. Extended backtest.csv with explicit `rule_name`, fee columns, and `_pct`
    columns per the deliverable spec; re-ran all three scripts (backtest,
    metrics, chart).
14. Wrote `output/equity.png` via `bin/chart.py` (pooled equity, net of taker,
    log scale). Verified PNG is valid via `file`. (This model cannot view
    images — verified the underlying data numerically instead, see below.)
15. Wrote `output/backtest_report.md`, `output/beginners_guide.md`.

Command count: ~14 bash invocations (several were one-shot inline python
verifications).

## Problems hit and solutions

- **Missing `ret` column** (my own script bug): the input CSV has only raw
  OHLCV; I wrote event-detection logic referencing a column I never created.
  Fixed by computing `pct_change()*100` per coin before the walk-forward split.
- **`Series.apply` over values, not index** (pandas pitfall): computing
  "coins alive per day" with `.apply(lambda day: ...)` on a series whose
  VALUES are floats passed the floats (NaN) to the lambda. Fixed by iterating
  the DatetimeIndex directly.
- **Inconsistent rule key labels**: RULE_LABEL and the loop keys drifted
  ("down" vs "A"). Unified to `("A"|"B"|"C", hold)`; added a unit-level print
  of every rule's totals to catch such drift next time.
- **Rule C gross total looked wrong (−42%)**: traced to the difference
  between pooled rebalancing and per-coin compounding; reconstructed the
  pooled series independently and matched the metric exactly. Documented the
  check rather than "fixing" a number that was actually correct.

## Anything that consumed context

- The full inherited AGENTS.md stack (fundamentals + e025 + ag-06 + ag-07),
  the ag-07 report (finding + definitions), and the ag-07 events.csv format.
- Cross-checking the equity chart: this model has no image input, so the chart
  was verified by reading `equity_daily.csv` at key dates (2025-02-03, 2025-06,
  2026-01, end) instead of viewing the PNG.

## Notes on data / results

- OOS window pooled: 2024-11-19 → 2026-08-13. Rule A trades: 28 on 8 distinct
  crash dates (2025-03-03 had 7 coins, 2025-10-10 and 2026-02-05 had 6 each).
- Rule A: +3.58% net-taker total, +1.24% expectancy, 68% win, −9.03% max DD.
  Rule B: −18.36%, −4.81% exp, 18% win. Rule C: −67.24% (bear-market window).
- Verdict per the pre-declared downgrade rule (28 < 30 trades): **directional
  evidence only**, stated explicitly in the report.

## End

2026-08-14 ~09:10 UTC. All deliverables present: backtest.csv, backtest_report.md,
equity.png, oos_windows.csv, per_coin.csv, equity_daily.csv, metrics.json,
beginners_guide.md, session-log.md, done.txt.
