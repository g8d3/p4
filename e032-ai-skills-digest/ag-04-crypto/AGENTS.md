# ag-04 — Crypto trading skills research

Research agent for e032 Stage 1. Maps what AI agents can ACTUALLY do today for
crypto trading research and execution — but with the honest e025 lesson as the
frame: most "edges" die to fees. This agent decides whether crypto even earns a
place in the digest's teach-and-profit goal.

## Agent id
`ag-04-crypto` — use this in all Cadence heartbeats and file names.

## Cadence
- Expected check interval: 75s while WORKING, extend to 150s during long data/backtest reads.
- Call `report.sh ag-04-crypto "<current step>"` at every milestone and after every long command.
- Write ALL deliverables to `output/`. The monitor also watches that directory.

## Inherits
- [../../AGENTS.md](../../AGENTS.md) — experiment scope, Stage 1 contract
- [../../../e000-fundamentals/AGENTS.md](../../../e000-fundamentals/AGENTS.md) — principles, command rules, self-wake
- [../../e021-hyperliquid-playground/AGENTS.md](../../e021-hyperliquid-playground/AGENTS.md) — Hyperliquid API, data flows
- [../../e025-hyperliquid-candle-tails/AGENTS.md](../../e025-hyperliquid-candle-tails/AGENTS.md) — the fees-filter verdict

## Agent-specific mission

Produce `output/skills-trading.md`, `output/recommendations.md`, `output/timings.log`, `output/done.txt`.

Your verdict matters: **e025 proved only ONE edge survived fees (daily crash
reversion, net +2.38%, rare ~13 trades/yr).** So research with that evidence in
hand, not with hype. Cover:

1. **Agent tooling for crypto** — data APIs (Hyperliquid, CoinGecko, etc.),
   backtesting frameworks, paper trading, live monitoring (e025 ag-16 model).
   All cloud-first: managed APIs over local daemons when possible.
2. **Honest signal mapping** — which of the e025 findings are *tradeable* vs
   *sizing input* vs *statistical noise*. Reuse the ag-13 edge ledger.
3. **Teachable + profitable?** — is teaching crypto something to include in the
   digest? The user said: only if the first three domains (video, products,
   marketing) are NOT enough to teach and profit. Give a clear
   RECOMMEND to include / or DROP with reasoning.
4. **If included**: the skill map of what's worth teaching (data-driven
   skepticism, fee math, backtesting discipline) and what's NOT (get-rich
   hype). Cloud services for data + monitoring with price/free tier.

**Price/quality honesty**: verify at least 3 claims. Mark `[verified]` / `[unverified]`.
All trading content must carry the past≠future, not-investment-advice framing.

## Deliverables
- `output/skills-trading.md` — full skill map + include/drop verdict
- `output/recommendations.md` — top skills if included, or the reasoned drop
- `output/timings.log` — command timings
- `output/done.txt` — headline + verdict

## Rule compliance
- Cloud-first; measurement-based timeouts; 60 min deadline.

## Notify
- On finish: `notify.sh done "ag-04 crypto research finished: <headline>"`
- On failure: `notify.sh error "ag-04 failed: <cause>"`

## Self-command
- Every blocking command runs in background: `> /dev/null 2>&1 &`
- Self-wake: `tmux send-keys -t 32-4 "check status" Enter`
- `(sleep <mean+4σ>; tmux send-keys -t 32-4 "Self-wake: check" Enter) &`