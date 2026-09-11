# e057-launchpad-trading

Trading + LP strategies for launchpad-emitted tokens (any chain), and the product idea built on top.

## Documents

- [`README.md`](README.md) — what this experiment is, the three findings that changed the plan, next steps.
- [`STRATEGY.md`](STRATEGY.md) — the strategy system: base rates, levels, entry/exit/kill rules, sizing, LP rung algorithm, volume profile, measurement backlog.
- [`APP.md`](APP.md) — product spec: gap, MVP, data stack, monetization, social-volume feasibility, risks.
- `research/` — sourced research passes (one file per topic) plus the ladder math script.

## Conventions

- Research findings must carry a URL and date. Unsourced numbers are banned from these files.
- Confidence is marked per claim (high/medium/low) wherever evidence is thin.
- Corrections go in place, with the counter-evidence, not as silent edits.
- No code beyond reproducible math scripts in `research/` until the measurement backlog (G1-G3) is done.
- Reusable infrastructure lives elsewhere in this repo: `e025-hyperliquid-candle-tails/` (backtest
  harnesses, event studies), `e021-hyperliquid-playground/` (data ingestion + SQL),
  `e035-trading-video-alerts/` (level-proximity detection and alerting).
