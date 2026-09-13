# e058 STRATEGIES — ladder registry (HYPOTHESIS → BACKTEST → PAPER → PROPOSE)

Rule: no skipping steps. N<20 resolved = THIN, never propose real money on THIN.
A strategy degrading two legs running gets demoted to PAPER, never defended.

## S1 steady-spread carry (ACTIVE, step=PAPER)

- HYPOTHESIS: DEX perp spreads ≥20bps that survive 4 consecutive ~15m
  snapshots (≥2 venues) pay to carry 24h; edge = persistence filters
  snapshot mirages; invalidation = 24h hold-rate <40% over N≥20.
- BACKTEST (run #32, bin/backtest.py): 50.0% held 24h (4/8, window
  2026-09-12). N=8 → THIN.
- PAPER (run #33, /api/paper): auto-logs today's steady set on every card
  open (paper_calls, 1 row/coin/day); resolves each call at first snapshot
  ≥24h later (paper_outcomes); hit = spread still ≥20bps. Score served on
  the card + /api/paper.
- PROPOSE for real: only on e2e PASS + paper edge (≥55% over N≥20) + owner tap.
- Current score: backtest 50% (4/8, THIN) · paper collecting (day 1).
