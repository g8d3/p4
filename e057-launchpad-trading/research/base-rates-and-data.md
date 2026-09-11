# Base rates, filters, and data feasibility for launchpad token scoring + LP range planning

Research pass: 2026-09-10. Tooling: `tinyfish search / fetch / agent`. Confidence tags: [H] high, [M] medium, [L] low (snapshot/single secondary source). Every figure carries a source in the final section.

---

## Base rates

### 1. Survival — how many tokens die

**Aggregate (all chains on GeckoTerminal, Jul 2021 – Dec 2025)** [H]
- 53.2% of all cryptocurrencies ever listed on GeckoTerminal are no longer actively traded ("failed"). Universe: 25.2M+ tokens. Source: CoinGecko research, 2026-01-11 (updated 2026-04-17).
- Failures by year of last trade: 2021 = 2,584; 2022 = 213,075; 2023 = 245,049; 2024 = 1,382,010; 2025 = 11,564,909. 2025 alone = 86.3% of all failures in the window.
- Launches exploded from 428,383 (2021) to ~20.2M (2025). Q4 2025 alone: 7.7M deaths (34.9% of the 5-year total), attributed to the Oct 10 2025 liquidation cascade ($19B wiped in 24h).
- Methodology caveat: "failed" = no active trading after ≥1 trade; for pump.fun the study counted **only graduated** tokens. So this is a *graduated-token* death rate, not a bonding-curve rate — it is the closest thing to a post-graduation survival base rate that exists publicly. It is not a "price → zero" measure.

**Pump.fun, per-token lifespan (18.67M tokens, 2024-01-14 → 2026-06-18)** [H]
- ~68.7% (≈12.8M) recorded their **last trade on the same calendar day** they launched.
- +2.18M survived exactly one day → **>80% dead within 2 days**.
- Distribution: 770,249 (≈4%) 2–3 days; 642,614 (3.4%) 4–7 days; 460,697 (2.5%) 8–14 days.
- **Only 850,000 (4.55%) survived >90 days.**
- Source: CoinGecko report, 2026-06, via Cryptopotato 2026-06-24 / KuCoin 2026-06-25 / Bitget 2026-06-25. (Original CoinGecko page was bot-blocked; three independent secondary reports agree on 68.67%, 850K, 4.55%.)

**Pump.fun graduation rate — time series (the number is regime-dependent, do not use one value)** [H for the range]
| Period | Graduation rate | Source |
|---|---|---|
| Jan–Aug 2024 | 1.4% (1.8M tokens) | Bitget citing Dune, 2024-08-18 |
| Q4 2024 | <2% of mints reach a major DEX | arXiv 2512.11850 |
| Feb 17 – Mar 14 2025 | <1%, first sustained 4-week streak | Cointelegraph via TradingView, 2025-03-14 |
| Apr 2025 | 0.37% – 1.78% | Smithii |
| Sep–Oct 2025 | **0.198% pooled** (655,770-token sub-sample: 0.63%) | SSRN 6915560 |
| Jan 2024 – Jan 2026 (all 15.2M coins) | **1.02%** | arXiv 2609.10246 |
| 2026 weekly average | 0.26% | BitcoinFoundation, 2026-06-17 |
| 2026-01-29 single day | 269 tokens, >1% (highest since summer 2025 = 0.92%) | Cryptopolitan, 2026-01-29 |
- Conflicting outlier: a Coinmonks post claims "2.7% in a median of two minutes" — [L], inconsistent with every Dune-derived figure; treat as noise.

**Fraud / manipulation share** [M, mixed methods]
- Uniswap v2: >98% of tokens minted daily exhibit fraudulent characteristics (Kalacheva et al. 2026, ScienceDirect); an earlier label study found 26,957 scams vs 631 non-scams (97.7%) — [L] older dataset (Reddit r/CryptoCurrency).
- "Over 80% of memecoins experience rug pulls" (arXiv 2608.20271) — [L] single paper, unbalanced-data framing.
- Solidus Labs: ~98.7% of Pump.fun tokens and 93% of liquidity pools flagged fraudulent — [L] (report page unreachable; figure comes from search snippet only, methodology not inspected).
- Naviglio et al. 2025 (EPJ Data Science): a significant share of Uniswap v2 market liquidity is trapped in honeypots; high net-traded-value combined with low liquidity is a rug signal. [M]

**Per-chain gaps — evidence is thin or absent**
- **four.meme (BNB)**: ~384k tokens created, ~5,150 graduated → **≈1.34% graduation** [L], single Coinmonks article 2025-10-12; a Dune dashboard exists (`dune.com/four_meme/fourmeme`) but no peer-reviewed survival study found. Four.meme also added sliding fees to fight bots (Cryptorank).
- **HyperEVM / Hyperliquid HIP-1 spot**: no survival or post-listing drawdown study found. Structural fact known: the HIP-1 spot *listing fee* ran above $100k and HIP-1 is a capped-supply standard with on-chain spot order books (Binance research 2025-01-01; Hyperliquid docs 2026-06-05). A Dune dashboard tracks alt.fun (HyperEVM launchpad) tokens launched/graduated/graduation rate, but numbers were not extractable in this pass. Dune does host Hyperliquid and HyperEVM datasets. **This is a real, unfilled evidence gap for the product — you will be building the first base-rate table for it.**
- **Base**: only a generic "Base Meme Token Analysis" Dune dashboard (holder growth, price, volume, top holders) was found; no cohort survival study. [Gap]
- **Solana (platform-level, not per-token)**: Pump.fun peaked at 71.1% of all Solana token mints and 40–67.4% of DEX transactions in Q4 2024 (arXiv 2512.11850) — context, not a survival rate.

### 2. Rebound after deep drawdown — **weakest evidence area; mostly undocumented**

What is actually documented:
- Meme-coin sector: equally weighted portfolio of the ten largest meme coins returned **−78.74%** over Jan 2025 – Feb 2026, underperforming all benchmarks (Krause, SSRN, 2026) [M via search snippet; SSRN full text bot-blocked].
- Sector-level: meme market cap fell ~82% / ≈$110B from its 2024 peak by Jun 2026 (yellow.com, BitcoinFoundation 2026-06) [L, news].
- Survivorship/delisting bias: across 3,904 cryptocurrencies (2014–2021), annualized survivorship bias is **62.19% equal-weighted vs 0.93% value-weighted** — i.e. equal-weighted crypto indices are massively distorted by tokens that die; most tokens never come back (Stoeckl, 2026-04-24) [M].
- The 68.7% same-day-death and 4.55% >90-day survival figures imply the *population of tokens that could ever rebound is already ~5% of launches* — this is the single most useful rebound base rate available today [H].

What is NOT documented (do not invent it):
- No dataset or study was found that answers "after −50% / −80% / −95% from ATH, what fraction of tokens recovers +50% / +100% / 10x, and over what horizon." Searches for "buy the dip" base rates returned BTC/equity drawdown analyses (Owen Analytics, Medium/The Capital), which are **not** memecoin base rates and must not be reused as such.
- No public "time-to-death" curve per drawdown bucket was found beyond the lifespan table above.
- The only drawdown-recovery datapoint encountered is a single trader anecdote (held through −90%, then +2,100%; Cryptorank 2025-01-10) — **anecdote, not a base rate**.

**Implication for the design doc:** the rebound/recidivism question is where the product can create proprietary value, because the public evidence does not exist. It requires your own trade-level dataset (which Topic B shows is obtainable, but only by aggregating trades yourself).

### 3. Filters that seem to work (documented predictive value)

| Filter | Evidence | Confidence |
|---|---|---|
| **Speed of liquidity accumulation** (SOL bonded per trade / trades to reach a curve level) | Strongest predictor of graduation, dominating all other variables across the whole bonding-curve range. Fast accumulation through *few* trades = higher graduation probability. Pump.fun, time-consistent features. arXiv 2602.14860 (2026-02-16) | [H] for the paper; single platform |
| **Bot-like / algorithmic trading intensity** | Systematically *lower* graduation probability beyond intermediate curve stages — high turnover ≠ committed capital. arXiv 2602.14860 | [M] |
| **Creator/deployer address clustering (serial launchers)** | Top-1% creator address groups create **58.6% of all 15.2M** pump.fun coins (grouped by funding patterns); confirms serial-launcher concentration is measurable. arXiv 2609.10246 | [H] for concentration; predictor power not quantified |
| **Wash-trading contamination of volume** | ≥4M wash trades = **17% of all trading transactions**; wash trading can inflate graduation probability **up to 10×**. Therefore raw volume/velocity is a poisoned signal. arXiv 2609.10246 | [H]; Chainalysis 2025 independently: ~43% of one examined token's Uniswap volume was wash trading, 3.59% of launched tokens facilitate short-lived manipulation [M] |
| **Copycat detection (name/symbol/description/image)** | ≥1.5M coins (>10%) are copies of originals; originals are "much more successful" than copies. arXiv 2609.10246 | [M] |
| **Coordinated sell / insider dump pattern** | ~8,000 detected instances (conservative criteria) using address consolidation before a single dump. arXiv 2609.10246 | [M] |
| **Social-post linkage** | 3.5M coins (23.5%) created within the wake of a Twitter/Truth Social post; 31 specific posts let creators earn ≥$1M each → social→launch latency is a real, exploitable signal. arXiv 2609.10246 | [M] |
| **Historically successful traders entering early** | Modest and **non-monotonic** effect (they accelerate discovery then exit fast). arXiv 2602.14860 | [M] |
| **High net-traded-value + low liquidity** | Rug/honeypot risk flag on Uniswap v2. Naviglio et al., EPJ Data Science 2025-12-30 | [M] |
| **Contract-level rug features (code + tx)** | RPHunter: 95.3% precision / 93.8% recall on 645 labelled rug pulls — proves detection is feasible, not that a filter generalizes. arXiv 2506.18398 | [M] |
| **Creator pre-graduation liquidation** | Systematic pump-and-dump by creators around the graduation transition is structurally incentivized by the bonding-curve → real-AMM switch. arXiv 2602.14860 | [M] |

**Claimed-but-unquantified (treat as anecdote until you measure it):** holder concentration, unique holders per mcap, LP locked/burned, buy/sell pressure balance, sniper concentration. Only qualitative support found (e.g. Cryptopolitan 2026-01-29 notes newly graduated tokens "are still heavily sniped or controlled by insiders"; the standard rug-filter checklist in the Four.meme tooling writeup). **No located study gives a hit rate for any of these as entry filters.** These are hypotheses for your own backtest, not inputs you can cite.

Also note the counter-evidence baked into the base rate: because graduation itself is ~0.2–1.4% depending on regime, **any** filter must be judged against that prior, and the arXiv 2602.14860 paper explicitly frames graduation probability as needing to beat a naive buy-and-hold breakeven to be economically meaningful.

---

## Data & API feasibility (table)

| Provider | Chains / Arc 5042 | OHLCV | Trades | Holders | Real-time | Free tier / rate limit | Rough price | Conf. |
|---|---|---|---|---|---|---|---|---|
| **DexScreener** | Multi-chain EVM + Solana; Arc not listed | Not in documented public endpoints | No public trade feed | No | Polling only (latest token profiles / boosted tokens) | No API key; **300 req/min** pair & pool endpoints, **60 req/min** token-profile endpoints | Free, no paid tier | [H] docs.dexscreener.com; CoinGecko 2026-08-30 |
| **GeckoTerminal (CoinGecko /onchain)** | Multi-chain; Arc not listed | Yes | Yes (per-pool) | No | 1-min cache; data 2–3s after confirmation | Public API **~10 calls/min** on api docs (**30/min** per FAQ — treat 10 as the safe number) | Free; higher limits via any paid CoinGecko plan | [H] api.geckoterminal.com/docs |
| **Birdeye** | Solana (+EVM); Arc no | Yes | Yes | Yes | Yes | Package-dependent, "low rate limit" in beta per docs | **x402 pay-per-request at $0.003/request** (2026-04-16) | [M] docs.birdeye.so |
| **Mobula** | Multi-chain; Arc no | Yes | Yes | Yes | Yes | **10,000 monthly credits, 1 RPS** free | 99.9% SLA from $750 | [M] docs.mobula.io |
| **Moralis** | EVM + Solana; Arc no | Yes | Yes | Yes (balances) | Streams | Credit-based free tier; CU estimator on pricing page | Pay-as-you-go CU pricing | [M] moralis.com/pricing |
| **Codex** | 60+ endpoints, EVM/Solana; Arc no | Yes | Yes | Yes | Yes | **15K credits free** | Paid from **$29/mo** | [M] codex.io 2026-05-06 |
| **Bitquery** | Solana, BSC (incl. a dedicated **Four.meme API**: bonding curve, live trades, OHLC, top traders); Arc no | Yes | Yes | Partly | **Yes — real-time streams; token-creation events are real-time only** | GraphQL, indexed filters; free tier exists (not verified) | Custom/enterprise | [M] docs.bitquery.io |
| **Solana Tracker** | Solana | Yes | Yes | Yes | Yes | Free tier reported at 10,000 req/mo | Data API credit plans in EUR (annual −30%); RPC plans separate; "Growth from $350/mo" cited by a third party | [M] docs.solanatracker.io; cex.io 2026-07-13 |
| **Helius** | Solana | Yes | Yes | via DAS/RPC | **Webhooks + Geyser-enhanced WebSockets** | Free tier exists (limits not verified) | RPC/webhook plans | [M] helius.dev |
| **Vybe** | Solana | not verified | not verified | not verified | not verified | not verified | not verified | [—] no data gathered this pass |
| **Alchemy** | 100+ chains; Arc not confirmed | via enhanced APIs | via APIs | via APIs | Webhooks/streams | **30M CU/month free**, pay-as-you-go **$0.40/1M CU** | Enterprise SLAs | [H] alchemy.com/pricing |
| **QuickNode** | 78+ chains incl. Hyperliquid; Arc not confirmed | via add-ons | via add-ons | via add-ons | Streams | Free tier exists | Usage-based | [M] quicknode.com |
| **GetBlock** | **ARC supported via JSON-RPC** | n/a (RPC) | n/a | n/a | n/a | n/a | n/a | [M] docs.getblock.io 2026-08-18 |
| **The Graph** | **Arc mainnet, eip155:5042, native USDC** | subgraph-dependent | subgraph-dependent | subgraph-dependent | subgraphs | Hosted/decentralized pricing | Per-query | [M] thegraph.com |
| **Dune** | Solana, HyperEVM, Hyperliquid (raw + decoded) | via SQL | via SQL | via SQL | via API | Free community queries; API on paid plans | Paid plans | [M] docs.dune.com |

**Arc (chain ID 5042) status:** infrastructure-level support exists (GetBlock JSON-RPC, The Graph chain `arc`, Uniswap SDK `ChainId.ARC = 5042` with v3/v4 address blocks). **No confirmation that DexScreener, GeckoTerminal, Birdeye, Mobula, Moralis, Codex or Solana Tracker index Arc.** Practical consequence: for Arc you either (a) run your own indexer on top of an RPC (GetBlock/Alchemy-class) or (b) use Dune if/when Arc data lands there. [M for the supports; H that no aggregator coverage was found]

**Volume profile / volume-at-price for DEX tokens:** no off-the-shelf product was found that computes horizontal volume-at-price / volume profile for DEX tokens. Providers give OHLCV (GeckoTerminal, Birdeye, Codex, Mobula) and trade-level streams (Bitquery, Helius, Moralis) — the profile must be built by bucketing individual trades into price bins. Cost implication: need trade-level ingestion, not just candles; GeckoTerminal's public trade endpoint (10 req/min) is the cheapest path for spot checks, Bitquery/Helius/Moralis streams for continuous coverage. TradingView-style volume profile exists only for CEX-listed instruments. [M — absence of evidence across ~5 searches; treat as "not found", not "does not exist"]

**Real-time launch/pool triggers:**
- Solana: Helius Webhooks and Geyser-enhanced WebSockets (lowest latency practical option); raw `logsSubscribe`/Geyser plugin streaming; Bitquery streams token-creation events in real time. [M]
- EVM/BNB: Bitquery Four.meme API streams live trades and bonding progress; Moralis Streams and QuickNode Streams for generic event webhooks; otherwise subscribe to factory contract logs over a node WebSocket. [M]
- Hyperliquid/HyperEVM: HyperCore spot deploys are HIP-1 actions; Hyperliquidity (HIP-2) quotes every 3s. Dune hosts HyperEVM data. No productized "new HIP-1 listing" stream was found — likely means watching the deploy action / builder-deployed contracts directly. [L — gap]
- DexScreener/GeckoTerminal: no documented push stream; polling "latest" endpoints within rate limits.

---

## Social volume feasibility

### X / Twitter
**Official X API (2026 pricing model):** moved to **pay-per-usage** — post read **$0.005 per post fetched** (X dev community pilot announcement), with per-app monthly caps (one cited cap: 2M reads/month); legacy subscription tiers (Free $0, Basic $200/mo, Pro $5,000/mo) are being retired and Basic is closed to new signups; some third-party breakdowns quote $0.005–$0.010 per call. Owned reads were repriced to $0.001 effective 2026-04-20. [H for the $0.005/read figure, M for the per-account caps and tier-retirement status]

Practical read: at $0.005/read, monitoring a few hundred candidate tokens × tens of posts each is cheap; continuous firehose monitoring of a launch stream is not. There is **no free tier** for new developers.

### Third-party social analytics
| Product | Public pricing found | Conf. |
|---|---|---|
| **LunarCrush** | Free "Discover" tier; **Individual $90/mo, Builder $300/mo, Scale $900/mo**, Enterprise custom; all paid plans include MCP access | [H] lunarcrush.com/pricing |
| **Kaito, TweetScout, Cookie3, Elfa AI, Santiment, Xtended/FollowerAudit** | **No pricing verified in this pass** — treat as unknown; do not put numbers in the design doc without a follow-up check | [—] |

### TinyFish CLI as an X substitute — tested, not assumed
- `tinyfish fetch content get "https://x.com/search?q=pump.fun&f=live"` → **fails usefully**: 302 to `/i/jf/onboarding/web?redirect_after_login=%2Fsearch...`; returned only login-wall boilerplate ("We've detected that JavaScript is disabled…", "Continue with phone/Apple"). **Zero posts, zero fields.** Latency ~9.3s. [H]
- `tinyfish fetch content get` on an `x.com/<user>/status/<id>` URL → `page_not_found`. [H]
- `tinyfish agent run --url "https://x.com/Dune" "extract 5 recent posts as JSON"` → **works logged-out**, COMPLETED in **~41s** (20:15:37 → 20:16:18), returned 5 posts with these exact fields: `text` (full post body), `date` (relative: "11h", "Sep 9"), `replies`, `reposts`, `likes`. Not returned: absolute timestamps, author handle per item, impressions, bookmarks, media URLs, quoted-post text, reply threads. [H — verbatim field list from the run output]
- Reliability caveat: the agent output is **LLM-extracted**, so counts are best-effort, not a typed API contract. Good for social-velocity *ranking* of a watchlist; not good enough to be an accounting-grade engagement metric. Rate limits/quotas for `agent run` are not documented in the CLI help and were not characterized beyond a single run.

**Verdict for the product:** TinyFish `agent run` on x.com profiles is a viable low-cost substitute for coarse social-volume/velocity signals (no API key, no per-read fee), with two limits: profile-scoped (not keyword-firehose) and relative-date only. If you need keyword streams or exact engagement, budget the official X pay-per-usage reads.

---

## Gaps / what cannot be measured cheaply

1. **Post-graduation downside/rebound base rates** — no public dataset answers drawdown-then-recovery fractions or time-to-death per drawdown bucket. Must be built from trade-level data. Highest-value proprietary dataset for the product.
2. **HyperEVM / HIP-1 spot survivorship** — no study, no ready dashboard numbers found. HIP-1's high listing fee (>$100k) is a natural filter but its effect on post-listing survival is unmeasured.
3. **Base chain (and four.meme) cohort survival** — no peer-reviewed cohort study; only platform-level Dune dashboards.
4. **Holder concentration / LP-lock / sniper-concentration as *predictive* filters** — universally used by rug-check tools, but no located study reports their lift versus the ~0.2–1.4% graduation prior. Requires backtesting.
5. **Global real-time new-pool detection feed** — no single product streams new pools for every chain; you assemble it per chain (Helius/Geyser for Solana, Bitquery or node logs for EVM, direct HIP-1 deploy watching for Hyperliquid).
6. **Volume profile for DEX tokens** — must be computed from trade-level data; no vendor sells it. Trade-level data is cheap only at low volume (GeckoTerminal 10 req/min) and gets expensive/polling-bound at scale.
7. **Arc (5042) analytics coverage** — RPC/graph access exists, aggregator coverage unconfirmed. Plan on self-indexing.
8. **Clean social data** — X has no free tier and pay-per-read pricing; keyword firehose is expensive. TinyFish agent gives profile-scoped, relative-date, LLM-extracted metrics only. Kaito/TweetScout/Cookie3/Elfa/Santiment pricing unverified in this pass.
9. **Wash-trading contamination** — 17% of pump.fun trades are wash trades and can inflate graduation odds up to 10×. Any scoring model that ingests raw volume without de-washing is fitting manipulation.
10. **Survivorship bias in any backtest you run** — equal-weighted crypto indices overstate returns by ~62% annualized (Stoeckl 2026); token universes must include dead tokens or results are meaningless.

---

## Sources

| URL | Date | One-line claim |
|---|---|---|
| https://www.coingecko.com/research/publications/how-many-cryptocurrencies-failed | 2026-01-11 (upd. 2026-04-17) | 53.2% of all GeckoTerminal-listed cryptos are dead; 11.6M failed in 2025 = 86.3% of all failures since 2021; graduated pump.fun tokens included in the universe |
| https://www.cryptopolitan.com/11-6m-tokens-failed-led-by-meme-coin-crash/ | 2026-01-12 | Popular summary of the above: 7.7M Q4-2025 deaths, Oct 10 2025 $19B liquidation cascade |
| https://cryptopotato.com/nearly-70-of-pump-fun-tokens-die-on-launch-day-coingecko/ | 2026-06-24 | CoinGecko: 18.67M pump.fun tokens; 68.7% last trade same day; >80% dead within 2 days; only 4.55% (850K) survived >90 days |
| https://www.kucoin.com/news/flash/nearly-70-of-pump-fun-tokens-disappear-on-launch-day | 2026-06-25 | Independent restatement of the 68.67% / 4.55% figures |
| https://www.bitget.com/news/detail/12560604161427 | 2024-08-18 | pump.fun graduation rate 1.4% on 1.8M tokens (Dune) |
| https://es.tradingview.com/news/cointelegraph:56f07a8fa094b:0-pump-fun-memecoins-are-dying-at-record-rates-less-than-1-survive/ | 2025-03-14 | Graduation rate below 1% for four straight weeks (Dune) |
| https://papers.ssrn.com/sol3/Delivery.cfm/6915560.pdf?abstractid=6915560 (unreachable; figures from search index) | 2026 | "Pump.fun Graduation Regime Windows": pooled graduation rate 0.198% (Sep–Oct 2025), 0.63% in a 655,770-token sample; 12.8M tokens by Oct 2025 |
| https://arxiv.org/abs/2602.14860 (full text: /html/2602.14860v1) | 2026-02-16 | Bonding-curve SOL as state variable; fast liquidity accumulation via few trades = strongest graduation predictor; bot-like activity lowers graduation odds beyond mid-curve; successful-trader entry = modest non-monotonic effect; creators systematically dump around graduation |
| https://arxiv.org/html/2609.10246v1 | 2026 | 15.2M pump.fun coins (Jan 2024–Jan 2026); 1.02% graduate; wash trades = 17% of all trades and can raise graduation odds up to 10×; top-1% creator groups make 58.6% of coins; ≥1.5M copycats; ~8,000 coordinated sells; 3.5M coins follow a Twitter/Truth Social post |
| https://arxiv.org/html/2512.11850v3 | 2025-12 | Q4 2024: pump.fun = up to 71.1% of Solana mints, 40–67.4% of DEX txs; <2% of tokens reach major DEXs |
| https://www.sciencedirect.com/science/article/pii/S2096720925000636 | 2026 (Kalacheva et al.) | >98% of tokens minted daily on Uniswap v2 exhibit fraudulent characteristics |
| https://link.springer.com/article/10.1140/epjds/s13688-025-00602-5 | 2025-12-30 (Naviglio et al.) | Honeypots trap substantial Uniswap v2 liquidity; high net-traded-value + low liquidity signals rug pull |
| https://arxiv.org/html/2608.20271v1 | 2026 | "Over 80% of memecoins experience rug pulls" (single paper, low weight) |
| https://www.soliduslabs.com/reports/solana-rug-pulls-pump-and-dumps-crypto-compliance (unreachable) | n/a | Snippet claims ~98.7% of pump.fun tokens and 93% of LPs flagged fraudulent — unverified |
| https://arxiv.org/html/2506.18398v3 | 2025 | RPHunter: rug-pull detection at 95.3% precision / 93.8% recall on 645 labelled incidents |
| https://arxiv.org/html/2507.01963v2 | 2025 | Case study: all rug-pulled tokens showed evidence of prior manipulation (small sample) |
| https://www.chainalysis.com/blog/crypto-market-manipulation-wash-trading-pump-and-dump-2025/ | 2025 | ~43% of one token's Uniswap volume was wash trading; 3.59% of launched tokens facilitate short-lived manipulation |
| https://www.sebastianstoeckl.com (paper page) | 2026-04-24 | Across 3,904 cryptos 2014–2021, annualized survivorship bias 62.19% equal-weighted vs 0.93% value-weighted |
| https://papers.ssrn.com (Krause, "An Empirical Analysis of Meme Coin Performance: 2025–2026"; abstract via search) | 2026 | Equal-weighted portfolio of the 10 largest meme coins returned −78.74%, underperforming all benchmarks |
| https://medium.com/coinmonks/four-meme-guide-api-and-trading-platforms-873160bf5d58 | 2025-10-12 | four.meme: ~384k tokens created, ~5,150 graduated (~1.34%); Dune dashboards and Bitquery Four.meme API for live data |
| https://docs.bitquery.io/docs/blockchain/BSC/four-meme-api/ | 2026 | Bitquery Four.meme API: live trades, bonding-curve progress, OHLC, top traders |
| https://www.binance.com (Hyperliquid product/economic analysis) | 2025-01-01 | Hyperliquid spot listing fee sustained above $100k/month |
| https://hyperliquid.gitbook.io (HIP-1 native token standard) | 2026-06-05 | HIP-1 = capped-supply fungible token standard with on-chain spot order books |
| https://dune.com/adpthegreat/alt-fun-analytics-hyperevm-launchpad | n/a | alt.fun (HyperEVM) dashboard tracks tokens launched, graduated, graduation rate, USDC volume (numbers not extracted) |
| https://docs.dune.com/data-catalog/evm/hyperevm/overview | n/a | HyperEVM and Hyperliquid available as Dune datasets (raw blocks, txs, logs) |
| https://docs.dexscreener.com | 2026-04-13 | DexScreener API: 300 req/min token-pairs endpoints; free, no key |
| https://www.coingecko.com (Top Onchain DEX Data APIs) | 2026-08-30 | DexScreener: no API key, 60 req/min token-profile endpoints, 300 req/min pair/pool endpoints |
| https://api.geckoterminal.com/docs | current | GeckoTerminal public API: OHLCV, trades, pools, tokens; 1-min cache; ~10 calls/min public |
| https://apiguide.geckoterminal.com (FAQ) | 2024-09-20 | GeckoTerminal public rate limit stated as 30 calls/min |
| https://docs.birdeye.so + https://birdeye.so x402 announcement | 2026-04-16 | Birdeye x402 pay-per-request at $0.003/request; beta APIs have low rate limits |
| https://docs.mobula.io (Pricing) | current | Mobula free: 10,000 monthly credits at 1 RPS; 99.9% SLA from $750 |
| https://moralis.com/pricing | current | Moralis credit-based (CU) free tier + pay-as-you-go |
| https://www.codex.io (Best Crypto APIs 2026) | 2026-05-06 | Codex free tier 15K credits across 60+ endpoints, paid from $29/mo |
| https://docs.solanatracker.io (Pricing & Limits) | current | Solana Tracker Data API credit plans in EUR, annual −30%; separate RPC plans |
| https://blog.cex.io (Top 5 Solana APIs for Developers) | 2026-07-13 | Solana API market: free 10k req/mo, Growth from $350/mo (attributed to one provider, not verified) |
| https://www.helius.dev/solana-webhooks-websockets | current | Helius webhooks + Geyser-enhanced WebSockets for real-time Solana events |
| https://www.helius.dev/blog/how-to-fetch-newly-minted-tokens-with-helius | current | Pattern for watching newly minted SPL tokens |
| https://bitquery.io/blockchains/solana-blockchain-api | current | Bitquery: real-time Solana streams, token-creation events real-time only, Geyser plugins |
| https://www.alchemy.com/pricing | current | Alchemy free 30M CU/month; pay-as-you-go $0.40/1M CU |
| https://docs.getblock.io (ARC) | 2026-08-18 | GetBlock provides JSON-RPC access to Arc |
| https://thegraph.com (Arc Mainnet) | current | The Graph supports `arc`, eip155:5042, native currency USDC |
| https://github.com/Uniswap/sdk-core (playbook/chains/arc.md) | current | Uniswap SDK `ChainId.ARC = 5042` with v3/v4 address blocks shipped |
| https://docs.x.com/x-api/getting-started/pricing | current | X API is pay-per-usage with credits and spending limits |
| https://devcommunity.x.com/t/announcing-the-x-api-pay-per-use-pricing-pilot/250253 | current | Post (read) = $0.005 per post fetched; existing tiers (Free $0, Basic $200/mo, Pro $5,000/mo) remain for now |
| https://devcommunity.x.com/t/x-api-pricing-update-owned-reads-now-0-001-other-changes-effective-april-20-2026/263025 | 2026-04-20 | Owned reads repriced to $0.001 |
| https://www.blotato.com/blog/twitter-api-pricing · https://postproxy.dev/blog/x-api-pricing-2026/ | 2026 | Third-party summaries: Basic retired for new signups; per-post reads $0.005–$0.010; monthly read caps ~2M |
| https://lunarcrush.com/pricing | current | LunarCrush: free Discover; Individual $90/mo, Builder $300/mo, Scale $900/mo, Enterprise custom; MCP on paid plans |
| tinyfish CLI runs (this pass) | 2026-09-10 | `fetch` on x.com search redirects to login (0 posts); `agent run` on x.com/Dune returned text + relative date + replies/reposts/likes in ~41s |
