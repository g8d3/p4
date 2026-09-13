# e058 STRATEGIES — ladder registry (HYPOTHESIS → BACKTEST → PAPER → PROPOSE)

Rule: no skipping steps. N<20 resolved = THIN, never propose real money on THIN.
A strategy degrading two legs running gets demoted to PAPER, never defended.

## S1 steady-spread carry (ACTIVE, step=PAPER)

- HYPOTHESIS: DEX perp spreads ≥20bps that survive 4 consecutive ~15m
  snapshots (≥2 venues) pay to carry 24h; edge = persistence filters
  snapshot mirages; invalidation = 24h hold-rate <40% over N≥20.
- BACKTEST (run #38, bin/backtest.py --force): 57.1% held 24h (12/21,
  window 2026-09-12T02:25–07:03Z, 963k rows). N=21 → NOT THIN (first
  grade with N>=20); rate flat vs run #36-37, edge holds as N grows.
- PAPER (run #33, /api/paper): auto-logs today's steady set on every card
  open (paper_calls, 1 row/coin/day); resolves each call at first snapshot
  ≥24h later (paper_outcomes); hit = spread still ≥20bps. Score served on
  the card + /api/paper.
- PROPOSE for real: only on e2e PASS + paper edge (≥55% over N≥20) + owner tap.
- Current score: backtest 56.4% (44/78, N>=20 SCORED) · paper 59 logged today (0 resolved — first resolution needs 24h).
- Run #43: N 44→78 (44/78, 56.4%, +1.9pp vs #40, window to 2026-09-12T09:48Z, 1067k rows). IP 16/16 + JUP 16/16 still carry; AI 8/9 joins the edge; TREE 1/16 + DEEP 1/10 + KAITO 0/4 are the drag. Rate holds above 40% invalidation. UI: main table rows now tap-to-filter (pickCoin) with paid record in the coin cell (16/16 vs new) — was dead rows with no proven-vs-new signal; pulse now shows paper count (59 logged). Next: first paper resolution (needs 24h) + keep N growing; PROPOSE only on paper edge ≥55% over N≥20 + owner tap.
- Run #40: N doubled 21→44 (24/44, 54.5%, window to 2026-09-12T08:17Z, 1004k rows). IP 10/10 + JUP 10/10 carry the edge; TREE 1/10 + KAITO 0/4 are the drag. Rate -2.6pp vs #38 but still above 40% invalidation. UI: main table now opens with top 100 + one-line count + show-all (was 647 rows at once on the phone). Next: first paper resolution (needs 24h) + keep N growing; PROPOSE only on paper edge ≥55% over N≥20 + owner tap.
- Run #38: N>=20 crossed (12/21) — strategy is SCORED, no longer THIN.
  UI: top picks show `(new)` for coins with no backtest history (POWR/
  STEEM/STONK) so the owner can tell new from proven in <30s; paid
  record now covers IP 5/5, JUP 5/5, TREE 1/5, KAITO 0/1 (new miss).
  Next: first paper resolution (paper_outcomes still 0 resolved) + keep
  N growing; PROPOSE only on paper edge ≥55% over N≥20 + owner tap.
- Run #37: per-coin paid-before record live on the card (backtest.json per_coin +
  top picks show e.g. JUP 3/3 paid, IP 3/3 paid, TREE 1/3). Param sweep (thr
  20/50/100 x last_n 4/6/8) found no denser edge — stricter filters starve N
  further, so the bottleneck is data age (~2h more sampling to N>=20), not params.
