# Swarm Market pricing — ranked (conversion x margin x ease)

Fee: 5% (`fee_bps` 500, mock math in v0, Stripe Connect later).

## Ranked models (all 10)

1. `per_run` — flat per execution. Wins when work is bounded and demoable (video cuts, audits).
2. `per_result` — pay on accepted result. Wins when quality varies and buyer trusts accept/reject.
3. `success_tip` (NEW) — tiny base + optional tip on wow. Wins when results delight unevenly (creative swarms).
4. `credits` (NEW) — prepaid bundles (e.g. 100 runs). Wins for repeat buyers; cuts checkout friction, prepays churn.
5. `one_time` — buy outright. Wins for self-hostable tools with near-zero marginal cost.
6. `per_seat_month` — rent seats monthly. Wins for always-on teams (support, ops swarms).
7. `per_token` — metered $/1k tokens. Wins for heavy LLM workloads with honest metering UI.
8. `stake_slash` (NEW) — buyer + seller stake escrow, slash on miss. Wins for high-stakes jobs needing commitment.
9. `auction` (NEW) — sellers bid down, buyers bid up per job. Wins for scarce/urgent capacity (launch week).
10. `revenue_share` — % of downstream earnings. Wins for money-making swarms (SEO, sales); needs trusted attribution.

## When to offer what

- New seller, no reviews: `per_run` + sandbox trial + `success_tip`.
- Repeat usage: graduate to `credits`, then `per_seat_month`.
- Risky/custom job: `stake_slash` or `auction`; settle disputes in escrow window.
- Evergreen tool: `one_time` with paid upgrades.

## New-model notes

- `success_tip`: base covers cost, tips are pure margin; show tip leaderboard.
- `credits`: bundles expire in 12 mo; breakage funds free trials.
- `stake_slash`: oracle = buyer accept + auto-accept timeout; slashed funds split buyer/seller/platform.
- `auction`: reserve price + deadline; platform fee on hammer price.
