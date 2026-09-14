# e066 — Arc Directory (numeric dApp atlas + monetizer)

The proof that e065 works: X is full of Arc-chain launch chatter
(launch in ~1–2 days, Sep 2026 — trading, investing, building).
This experiment is the web app the factory proposed: a directory of
Arc-chain dApps that is numeric-first, self-improving, and run by a
monetization agent. Third link: e064 → e065 → e066.

## Inherits
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — principles, mobile-first, quiet mode
- [../e062-agent-ops/DIRECTIVES.md](../e062-agent-ops/DIRECTIVES.md) — runner rules, DONE ladder, reporting format
- [../AGENTS.md](../AGENTS.md) — experiment index

## Goal

A mobile-first web directory of Arc-chain decentralized apps where
every listing is numbers, not blurbs:

- Per-chain + per-dApp time series from first day: TVL, txns, active
  users, fees/revenue, plus X-mention velocity fed from e064/e065.
  Multiple sources, every number timestamped + sourced.
- Self-improvement loop: usage + staleness events feed the 30-min
  runner leg, which ships one visible improvement per leg (new column,
  new source, better ranking — never polish without a moved number).
- Monetizer agent: its top objective is earning from the platform
  (listings, referrals, API tiers, sponsor slots — T1 auto, real money
  moves only via approved proposal) to fund its own improvements.
  Every money action logged tx-hash-first (tax-report-ready export).

## Proof numbers

- Coverage: dApps with fresh (<24h) numbers; series length in days.
- Revenue attempts: monetization experiments shipped + $ in/out.
- Beat tech half ends with `score coverage=<n_fresh>/<n_total>`.

## DONE ladder (e062 standard)

1. WORKING — runs locally, endpoints curl-verified, no secrets.
2. DEPLOYED — live tailnet URL, survives reboot, stale-badged data.
3. TESTED — e2e + numbers traceable to sources.
4. ANNOUNCED — owner ping with URL + what it proves.
5. MONETIZED — billing/referrals/API tiers, only after usage.
