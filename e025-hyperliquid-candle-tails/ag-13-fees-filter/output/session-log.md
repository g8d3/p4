# session-log — ag-13 fees filter

## Start

2026-08-14 ~08:30 UTC (opencode, opencode-go/deepseek-v4-flash, window 25-13)

## Task

Phase 5f: build the net-of-fees **edge ledger** — re-evaluate every candidate
edge from the whole experiment after subtracting Hyperliquid fees and a
slippage assumption; separate "statistically interesting" from "tradeable".

## Inputs read

- Inherited AGENTS.md stack: e000-fundamentals, e025 experiment, ag-06
  (backtest rigor + fee model), ag-08 (OOS discipline, noted pending).
- Reports (all exist): ag-02 (fat tails), ag-03 (conditional tails),
  ag-05 (seasonality/patterns), ag-06 (weekday permutation + backtest),
  ag-07 (3σ event study).
- **Pending / no output yet**: ag-08 (OOS crash backtest), ag-09 (funding),
  ag-10 (relative strength), ag-11 (vol model), ag-12 (regime drift).
  The crash-reversion row uses ag-07's numbers and is marked provisional.

## Commands run

1. `ls`/`wc` over sibling agent output dirs — confirmed which deliverables
   exist vs pending (ag-08..ag-12 empty).
2. `head` on `candles_raw.csv` / `stats.csv` / `patterns.csv` — column
   conventions for ret/pct columns.
3. Read full reports: ag-05 report.md, ag-06 backtest_report.md +
   permutation_test.md + strategy_spec.md + results.json, ag-07 report.md,
   ag-03 report.md, ag-02 report.md, comparison.md.
4. Wrote `bin/compute_ledger.py` — re-verifies the ag-07 crash-reversion
   numbers on the shared CSV (ret < −3σ per coin, next-5-candle cumulative),
   computes the post-crash next-candle bounce in % (5m/1h), the 1h
   body-position spread, and breakeven edges under 4 cost models.
   `timeout 300 python3 bin/compute_ledger.py`.
   - Crash reversion reproduced EXACTLY: mean +2.471%, median +3.069%, n=46,
     8/10 coins positive (ag-07 reported +2.5/+3.07, 6/6 same-sign on coins
     with enough data — consistent).
   - 5m post-crash p50 next = +0.049% (below 0.09% breakeven → dies).
   - 1h post-crash p50 next = +0.208% (survives taker, marginal).
   - 1h body reversion spread ~0.04% (below breakeven → dies).

## Problems encountered

- None blocking. One decision: used full-sample ag-07 numbers (not an OOS
  backtest) because ag-08 has no output yet — flagged provisional per
  AGENTS.md ("if ag-08 output does not exist, use ag-07 numbers").
- The breakeven math is deliberately the simple rule "gross edge per trade
  must exceed the round-trip cost" — stated as breakeven table, no fancy
  estimator needed for the verdict.

## Deliverables

- `output/edge_ledger.csv` — 9 rows, one per candidate edge, all numbers.
- `output/report.md` — verdicts per edge, ranking, capacity notes, final
  experiment verdict.
- `output/beginners_guide.md` — fees/slippage/breakeven for a beginner.
- `output/session-log.md` — this file.
- `done.txt` — final ledger verdict.

## End

2026-08-14 ~08:45 UTC. Verdict: one edge net-positive (daily crash reversion,
~26× fee, provisional on ag-08); most real edges die at 0.09% round trip.
