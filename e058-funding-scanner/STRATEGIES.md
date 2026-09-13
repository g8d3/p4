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
- Run #58: N 206→215 (113/215, 52.6%, -0.3pp vs #57, window to 2026-09-12T16:48Z, 1369k rows). IP 40/40 + JUP 40/40 still perfect; AI 14/19 holds; DEEP 14/34 edges up; drag TREE 1/40 + KAITO 0/16 + ONG 0/15 — second soft dip leg (-0.8, -0.3) but new-entrant dilution (+9 N), rate far above 40% floor, stays PAPER (watch next leg, not defended). UI: top card drops the contradictory `steady ✓ (no history yet)` — coins with no 24h record now read `new — holding so far`, legend gains the `new` line (server _verdict + JS plainV, first paint + live refresh). Next: first paper resolution (~12h) + keep N growing; PROPOSE only on paper edge ≥55% over N≥20 + owner tap.
- Run #57: N 190→206 (109/206, 52.9%, -0.8pp vs #55, window to 2026-09-12T16:19Z, 1348k rows). IP 38/38 + JUP 38/38 still perfect; AI 14/19 holds; DEEP 14/32 edges up; drag TREE 1/38 + KAITO 0/16 + ONG 0/14 — first dip leg since #52 (demote only if it repeats next leg), stays PAPER. Rate still above 40% invalidation. UI: paper ballot section live (ISSUES #8 — /api/paper/calls serves 77 calls + rule + first-grade countdown, titled details + inner-scroll table + refresh, auto-loads on paint) — predictions now a visible list, not just a count. Next: first paper resolution (~12h) + keep N growing; PROPOSE only on paper edge ≥55% over N≥20 + owner tap.
- Current score: backtest 52.9% (109/206, N>=20 SCORED) · paper 75 logged today (0 resolved — first resolution needs 24h).
- Run #55: N 162→190 (102/190, 53.7%, +1.8pp vs #52, window to 2026-09-12T15:17Z, 1296k rows). IP 35/35 + JUP 35/35 still perfect; AI 14/16 + ZHIPU 2/2 hold; DEEP 13/29 recovers (+5 new all hit); drag TREE 1/35 + KAITO 0/16 + ONG 0/14 — uptick after #52 dip, so no second degradation, stays PAPER. Rate still above 40% invalidation. UI: dark/light toggle moved from top-right into bottom thumbbar (was thumb-unreachable) — theme switch now one thumb tap. Next: first paper resolution (needs 24h) + keep N growing; PROPOSE only on paper edge ≥55% over N≥20 + owner tap.
- Run #52: N 139→162 (84/162, 51.9%, -2.1pp vs #49, window to 2026-09-12T14:03Z, 1255k rows). IP 30/30 + JUP 30/30 still perfect; AI 12/13 + ZHIPU 2/2 hold; DEEP 8/24 edges up; drag TREE 1/30 + KAITO 0/16 + ONG 0/12 — first degradation leg since #47 (demote only if it repeats next leg), stays PAPER. Rate still above 40% invalidation. Next: first paper resolution (needs 24h) + keep N growing; PROPOSE only on paper edge ≥55% over N≥20 + owner tap.
- Run #49: N 125→139 (75/139, 54.0%, +0.4pp vs #48, window to 2026-09-12T12:47Z, 1192k rows). IP 26/26 + JUP 26/26 still perfect; AI 12/13 holds; DEEP 7/20 recovers; TREE 1/24 + KAITO 0/13 are the drag — uptick, stays PAPER. Rate still above 40% invalidation. UI: top-3 picks now server-rendered tappable on first paint (was empty row until JS fetch) — owner taps a pay in <30s with no wait. Next: first paper resolution (needs 24h, ~16h to go) + keep N growing; PROPOSE only on paper edge ≥55% over N≥20 + owner tap.
- Run #48: N 112→125 (67/125, 53.6%, flat vs #47, window to 2026-09-12T12:19Z, 1172k rows). IP 24/24 + JUP 24/24 still perfect; AI 10/11 + ZHIPU 2/2 hold; TREE 1/24 + KAITO 0/11 + DEEP 5/18 + ONG 0/6 are the drag — flat, not a second degradation, stays PAPER. Rate still above 40% invalidation. UI: top card drops WATCH/STEADY jargon for plain words (steady ✓ / watch — thin backing / flippy) server-side + JS, one-line legend — owner reads the top pay in <30s. Next: first paper resolution (needs 24h) + keep N growing; PROPOSE only on paper edge ≥55% over N≥20 + owner tap.
- Run #47: N 89→112 (60/112, 53.6%, -4.8pp vs #45, window to 2026-09-12T11:34Z, 1151k rows). IP 22/22 + JUP 22/22 still perfect; AI 9/10 holds; TREE 1/22 + KAITO 0/9 + DEEP 3/16 + ONG 0/4 are the drag — new-entrant dilution, first degradation leg (demote only if it repeats next leg). Rate still above 40% invalidation. Next: first paper resolution (needs 24h) + keep N growing; PROPOSE only on paper edge ≥55% over N≥20 + owner tap.
- Run #45: N 78→89 (52/89, 58.4%, +2.0pp vs #43, window to 2026-09-12T10:19Z, 1109k rows). IP 18/18 + JUP 18/18 still carry; AI 9/10 + ZHIPU 2/2 join the edge; TREE 1/18 + DEEP 3/12 + KAITO 0/5 are the drag. Rate holds above 40% invalidation. UI: thumbbar gains 1-tap ✕ clear (was 3 taps to undo a coin filter: open filter, delete, refilter) — tap-coin loop now closes in one thumb tap. Next: first paper resolution (needs 24h) + keep N growing; PROPOSE only on paper edge ≥55% over N≥20 + owner tap.
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
