# e058 STRATEGIES — ladder registry (HYPOTHESIS → BACKTEST → PAPER → PROPOSE)

Rule: no skipping steps. N<20 resolved = THIN, never propose real money on THIN.
A strategy degrading two legs running gets demoted to PAPER, never defended.

## S1 steady-spread carry (ACTIVE, step=PAPER)

- HYPOTHESIS: DEX perp spreads ≥20bps that survive 4 consecutive ~15m
  snapshots (≥2 venues) pay to carry 24h; edge = persistence filters
  snapshot mirages; invalidation = 24h hold-rate <40% over N≥20.
- BACKTEST (run #36, bin/backtest.py --force): 57.1% held 24h (8/14,
  window 2026-09-12T02:25–06:17Z, 922k rows). N=14 → still THIN;
  evaluable window grows ~24h behind live sampling, N>=20 lands next leg.
- PAPER (run #33, /api/paper): auto-logs today's steady set on every card
  open (paper_calls, 1 row/coin/day); resolves each call at first snapshot
  ≥24h later (paper_outcomes); hit = spread still ≥20bps. Score served on
  the card + /api/paper.
- PROPOSE for real: only on e2e PASS + paper edge (≥55% over N≥20) + owner tap.
- Current score: backtest 57.1% (8/14, THIN) · paper logging (20 coins today).
- Run #37: per-coin paid-before record live on the card (backtest.json per_coin +
  top picks show e.g. JUP 3/3 paid, IP 3/3 paid, TREE 1/3). Param sweep (thr
  20/50/100 x last_n 4/6/8) found no denser edge — stricter filters starve N
  further, so the bottleneck is data age (~2h more sampling to N>=20), not params.
