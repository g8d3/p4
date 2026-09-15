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
- Current score (run #73): backtest 95.2% (119/125, coverage 20→30 protos, new Yield cat, DYDX id fixed) · paper 20 pending, first resolves ~30d.

## Deep-tier split (run #88)
- BACKTEST split: deep ≤0.5× 88/89 = 98.9% vs shallow 0.5–0.8× 31/36 = 86.1% (total 119/125 = 95.2%). The ★ deep tier validates: deepest cheap calls stay cheap far more reliably. Score line now carries the split first-paint + live. Paper still 0 resolved / 20 pending (30d window, first grades 10-14) — precision flat by construction until paper grades.

## Run #123 (2026-09-15)
- BACKTEST 119/124=96.0% (+2 hits vs run122 117/124=94.4%, trailing-12wk re-resolve, N=124 NOT THIN) · paper 0 resolved / 33 pending (30d window, first grades 10-14). First-paint was stale (117/124) until inject re-ran — writer-plus-inject now one chain. Stays PAPER (paper N=0). Next: hold LIVE badge daily; PROPOSE only on paper precision ≥60% over N≥20 + owner tap.
