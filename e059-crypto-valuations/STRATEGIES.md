# e059 STRATEGIES — ladder registry (HYPOTHESIS → BACKTEST → PAPER → PROPOSE)

Rule: no skipping steps. N<20 resolved = THIN, never propose real money on THIN.
Read-only track: PROPOSE here means owner-facing alert wording, never positions.
A strategy degrading two legs running gets demoted to PAPER, never defended.

## S1 cheap-vs-category value (ACTIVE, step=PAPER)

- HYPOTHESIS: coins priced ≤0.8× their category-median P/Fees (30d-annualised
  sales) stay below the median (ratio <1.0) a month later; edge = sales regime
  persistence; invalidation = precision <60% over N≥20.
- BACKTEST (run #35, bin/cheap_calls.py): 93.5% stayed cheap (72/77, weekly
  calls trailing 12wk, DISJOINT trailing-30d windows, resolve +30d). N=77, not
  THIN. Mcap held constant at latest (no free mcap history) — tests the sales
  trajectory, disclosed in caveats. A 7d window scored 1.000 during build and
  was discarded as window-overlap autocorrelation (shared 23/30 fee-days).
- PAPER (run #35, data/cheap_calls.jsonl + daily_ratios.jsonl): logs today's
  cheap set each refresh, resolves at first snapshot ≥ call+30d. Score served
  on the card (cheap_calls.json) + pre-rendered first paint. Current: 0/0
  resolved (8 pending, first outcomes ~30d).
- PROPOSE for real: only on e2e PASS + paper precision ≥60% over N≥20 + owner tap.
- Current score: backtest 93.5% (72/77) · paper collecting (day 1).
