# e058 — Funding Scanner (DEX perp funding arb, monetizable)

Loris-style funding-rate arbitrage scanner, DEX-only, executable-first:
every spread shown is gated by venue liquidity (OI + ±1% depth) and
fundable rails. API is paid at Loris ($79–499/mo) — we aggregate
venue-direct public APIs (no keys, clean ToS) and monetize later
(API subs + alerts + execution + DEX referrals).

## Status

Prototypes (proven 2026-09-12, not products):
- `bin/capture.sh` — timestamped Loris-table-equivalent funding snapshots
  via stealth headless CDP recipe (see skill `browser-extract`). 3 captures
  banked in /tmp (`loris_cap_*`, `loris_funding.json`).
- `bin/enrich.py` — per-leg OI + depth enrichment (HL/Aster/Paradex/
  Extended/Lighter). Units verified exact vs Loris UI (DEEP 887.4%, KORU
  389.5% reproduced to the decimal).
- e021-hyperliquid-playground — HL sampler + SQLite + SQL web UI
  (verification pending, see trail).

## Core decisions (from live data)

- `funding_rates` unit = **8h-normalized basis points**.
  `MAX_ARB_APY = spread_bps / 100 * 3 * 365`.
- Snapshot spreads decay in minutes (MEME 1093% → 291% in 30 min).
  Ship **persistence scoring**, never raw snapshots.
- Identical values 30+ min apart on 1h venues (KORU, DEEP) = suspected
  **stale feeds** → per-venue freshness badge (a feature, not a bug).
- OI rank 500+ + exotic-only legs = mirage. Gate everything.

## MVP scope (no billing until usage)

1. `venues.md` — THE venue table: Loris 28 DEX + DefiLlama TVL/vol +
   probe status (public funding/depth/OI API? deposit rail + cost?).
   Venue cut for MVP: 6–8 fundable DEXes.
2. Sampler: `capture.sh` on cron (15 min) → timestamped JSON series.
3. Store: SQLite (e021 pattern) — `funding(coin, venue, bps8, ts)`,
   `liquidity(coin, venue, oi_usd, depth1pct_usd, ts)`.
4. UI: APY-ordered table + OI + depth columns + freshness badges.
5. Alerts: Telegram on persistent (3+ samples) executable spreads.
6. Later: API keys + paid tiers, one-click execution, referrals.

## Sampler cron (live since 2026-09-12)

`bin/sample.sh` every 15 min (+0–150 s jitter): stealth capture →
`data/loris_cap_*.json` → `bin/load.py` → `data.db`. All ignored
(regenerable). Verify: `tail sample.log` (ends `sample OK`), row 8 of
CRON.md. First manual run banked snapshot #4 (see report).

## Conventions

- Every command: timeout it, background long runs, `close --all` browsers.
- Never print secrets. Paper-track before live. $50 single-spend cap.
- Venue APIs change — freshness tracking doubles as integration monitor.
