# e059 ISSUES — owner review 2026-09-13 (thin data)

## 1. Too few rows, thin categories (root)

20 protocols, 2 sources (DefiLlama fees + CoinGecko mcaps). Some
categories hold a single option — a comparison of one is not a
comparison. Wanted: 3+ options per category before any category is
shown as "covered". Thin categories get a `thin` badge, not silence.

## 2. Source hunt backlog (standing order — a leg works this, not debates it)

Free, keyless, fetchable today:
- DefiLlama more: `/volumes`, `/fees` chains view, yields pools
  (APY comparables), stablecoins (mcap series) — same host, new tables.
- Dexscreener free: pair liquidity/mcap/txns per token (already used
  by e060 — same keyless pattern, new columns here).
- The Graph free subgraphs: per-protocol usage series (volume, users)
  where a subgraph exists; skip where none.
- Public RPCs (read-only `eth_call`): on-chain reads need no key —
  first candidate: TVL-ish proxies where APIs lack them.
- CoinGecko more: `/coins/markets` already used — add
  `total_volume`, `price_change_7d` columns sitting in the same payload.

Rules: one source per leg, cached, e2e asserts row-count growth;
a source that yields nothing in 2 legs is dropped in writing.

## 3. Clone-before-pay (owner principle, see SPEND.md)

Any paid data need arrives with a clone quote first: what the
service does, what subset we need, what building it costs (legs +
infra), then buy-vs-build. Default: build the small subset.
