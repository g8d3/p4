# e059 — Serious Crypto Stats + Tokenized Stocks (TradFi multiples)

TradFi-grade valuation page for serious crypto + tokenized stocks:
P/E, PEG-style growth multiples, revenue/fees, over time + comparables.
Loris lesson applied: only executable, well-sourced numbers; freshness
badges on every feed.

## Starting assets

- e057-launchpad-tokens (token data pipelines + site pattern) and
  e057-launchpad-trading (levels/math).
- DefiLlama `/protocols` (TVL; fees/revenue endpoints exist: see e057
  `data/fees__*` files for the exact API shape).
- Token Terminal / Artemis (crypto fundamentals), xStocks/Ondo (tokenized
  equities), Aster stock perps (seen live in Loris universe: TSLA, AAPL,
  NVDA perps).

## Scope control

- v1: top 50 crypto protocols — fees/revenue annualised, P/F (price to
  fees), growth (30/90d), comparables table. Tokenized stocks v2.
- No trading. No wallet. Read-only data product.

## Spike result 2026-09-12 (subsession, web-verified)

Local head start: e057 already fetches CoinGecko mcap + DefiLlama
fees/revenue/holders-revenue series (`bin/fetch.py` keyless, cached) with
per-protocol methodology fields — multiples must cite them.
Best source: **DefiLlama (free, scripted)** for P/Fees-style multiples.
Token Terminal free = view/export only, API custom pricing; Artemis Lite
free manual, API Enterprise custom — cross-checks only, no paid API yet.
Tokenized stocks: no single free retail API; free routes via xStocks docs
API, Kraken xStocks symbols, Chainlink 24/5 equity feeds, UniswapX (Ondo).
xStocks = price tracker, Ondo GM = total-return; always show
mint-premium/discount + hours badge (US geo-blocked). Formulas: P/Fees
(30d-annualized), P/ProtocolRevenue, PEG-style on revenue CAGR,
Premium_token vs equity close — all freshness-badged + comparables.

## First tasks

1. Survey fundamentals sources (Token Terminal, Artemis, DefiLlama
   fees/revenue) — cost, coverage, API keys needed?
2. Define multiple formulas (P/annualised-fees, PEG analogue) + caveats.
3. Reuse e057 site pattern for the page.
