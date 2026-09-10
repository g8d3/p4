# e057 — Launchpad tokens: stats for buying the platforms themselves

User wants to buy **the launchpad platforms' own tokens** (not tokens launched by them).
This experiment builds the evidence base: price/mcap history per token, and "sales"
(platform fees, revenue, growth) over time.

## Inherits

- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — principles, quiet machine, notify

## Structure

```
e057-launchpad-tokens/
├── AGENTS.md        # this file
├── config.json      # tokens + DefiLlama fee-protocol candidates (single source of truth)
├── bin/
│   ├── fetch.py     # network: CoinGecko (mcap history) + DefiLlama (fees) → data/
│   └── report.py    # offline: data/ → output/report.md + output/charts/*.png
├── data/            # cached JSON (safe to delete; fetch.py rebuilds)
├── refresh.log      # appended by refresh.sh
└── output/
    ├── report.md    # the stats report (markdown)
    ├── stats.csv    # raw stats table
    ├── charts/      # 5 charts (PNG)
    └── site/        # STATIC WEBSITE (publishable): index.html + charts/
```

## Run

```bash
cd e057-launchpad-tokens
python3 bin/fetch.py     # ~5-10 min (CoinGecko free tier: 1 call / 20 s, backoff on 429)
python3 bin/report.py    # instant, offline
bash bin/refresh.sh      # both + logs (cron runs this daily at 10:25)
```

Git policy: `data/`, `output/`, `refresh.log`, `repo/` are ignored by p4 git — all generated, refetchable, and the site's real home is g8d3/launchpad-radar (CI-deployed). Only AGENTS.md, config.json and bin/ are tracked.

Auto-refresh: cron entry `25 10 * * * bin/refresh.sh` regenerates data, report, charts and site daily.
Publishing: `output/site/` is self-contained static HTML — copy/symlink into `sites/<domain>` to serve.

## Data sources

- **CoinGecko public API** — current price/mcap (`/coins/markets`), daily mcap history since listing (`/coins/{id}/market_chart?days=max`). No key; respect rate limits.
- **DefiLlama fees API** — dailyFees / dailyRevenue / dailyHoldersRevenue per launchpad protocol (`fees.llama.fi/summary/{slug}`). Protocol slugs discovered from the fees overview list.

## Metrics computed (per launchpad)

- token: price, mcap, 30d/90d/1y change, ATH + date, % below ATH, 24h volume
- platform fees: 1d / 7d / 30d / 90d / 365d, revenue, holders revenue (buybacks)
- fee growth: last 30d vs previous 30d
- liquidity (TVL) + platform DEX/aggregator volume (24h, 30d) — DefiLlama
- P/F ratio: mcap / annualized (30d × 12) fees
- pump.fun creation frontier: newest mint timestamp sampled every refresh (rate signal accumulates)

## Known gaps (verified dead/free-unavailable 2026-09)

- Social volume/reach: CoinGecko community_data → paid-only (returns null); X syndication + Reddit public JSON blocked. Needs LunarCrush/X API when monetizing.
- Tokens created per launchpad: no free aggregate API (Dune would work with a key).
- boot.fun, belive.fun: not listed anywhere reliable. DAO/POLS/SFUND: fees not tracked by DefiLlama.

## Pitfalls learned

- CoinGecko public tier 429s fast → 20 s spacing + 65 s backoff, cache everything.
- DefiLlama slugs are not documented; match by candidate list against `/overview/fees` slugs, verify by name.
- `days=max` needs `interval=daily` on free tier; without it, 5-min granularity and huge payloads.
