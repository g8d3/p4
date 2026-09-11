# Product spec: Launchpad Base-Rate Engine + Strategy/LP Planner

Web app, plus the monetization model. Companion to [`STRATEGY.md`](STRATEGY.md).
Bottom line up front: build the **measurement** product first (it is the moat and the marketing),
monetize the **planning/journal** layer by subscription, treat execution fees as additive, and
defer any token.

---

## 1. The gap, stated precisely

Every consumer terminal in this niche monetizes the same way: **~0.9-1.0% per trade, no
subscription, fee discount as the acquisition hook, revenue-share rebate as the affiliate hook**
(Axiom, GMGN, Photon, BullX, Trojan, Padre — all verified). Nobody sells a subscription, and nobody
sells plan-and-review tooling.

Three gaps are real, and they are not equally good products:

| Gap | Status | Verdict |
|---|---|---|
| **Calibrated, published base rates** — "this score bucket graduated 0.9% of the time over 90 days vs 0.2% for the bottom bucket", versioned, misses shown | Nobody does it. Terminals sell signals, not calibration. | **Best opening.** Also the hardest to fake, which is the point. |
| **Bot-adjusted social attribution** — report the paid/boosted share of mentions separately from organic, and cross-check posters against on-chain funding clusters | Kaito was publicly gamed and shut its Yaps program in Jan 2026. Nobody ships a de-contaminated metric. | **Sharpest technical differentiator.** Requires data nobody packages. |
| **Post-trade journal tying alert → plan → fill → post-mortem** | Genuinely empty | Real gap, unproven willingness to pay. The audience already pays 1%/trade for speed; journaling is a cost to the user now for a benefit later. Ship it as a retention feature, not the headline. |
| LP range planning for hours-old tokens | Over-sold in the original brief | **Only defensible on tokens with ≥2-4 weeks history and ≥$1M liquidity.** Below that: show simulated IL and fee ranges, labeled as simulation. |

**The revenue-model trap to name out loud:** the only sponsors with money here are launchpads, DEXes
and aggregators — precisely the parties whose inventory an honest base rate rates as failures. Ad
revenue and score integrity are in direct tension, so paid placement must be *detected and published
as a feature* (paid-share), not sold quietly.

---

## 2. Product shape

```
                    free, public, auditable            paid ($29-99/mo)
  ┌──────────────────────────────────────┐  ┌────────────────────────────────────────┐
  │  Base-Rate Scorecard (versioned)     │  │  Strategy Planner                      │
  │  - score + its measured base rate    │  │  - level grid + tranche schedule (§2.2) │
  │  - "what happened" per bucket        │→ │  - LP rung planner w/ entry+IL+fee math │
  │  - misses published                  │  │  - exit/kill rules as checklists        │
  │  Token pages (long-tail SEO)         │  │  - journal + post-mortem + hit-rate     │
  │  Alerts (Telegram + web)             │  │  - portfolio/correlation view           │
  └──────────────────────────────────────┘  └────────────────────────────────────────┘
                    ↑                                          ↑
              acquisition                                 revenue
                    └────────── affiliate 25-30% ──────────────┘
                    └──── optional execution (Jupiter integrator, keeps 80%) ────┘
```

**MVP scope (one chain, one venue, 4-6 weeks):** Solana + Meteora DLMM. Ingest swaps →
build OHLCV, volume-at-price, ATH/drawdown buckets → publish the base-rate table → scoring + alerts
→ planner with LP rung math → journal.

**Explicitly out of MVP:** execution, multi-chain, mobile, copy-trading, and anything token-shaped.

---

## 3. Data stack (verified limits and prices)

| Need | Source | Reality |
|---|---|---|
| Token/pool discovery + OHLCV | DexScreener (300 req/min pairs, 60 req/min token-profiles, no key, free), GeckoTerminal (~10-30 req/min, free) | zero-cost prototype is possible |
| Trade-level (for volume profile + base rates) | GeckoTerminal trades endpoint (spot checks) · Bitquery (real-time streams; dedicated Four.meme API with bonding-curve progress) · Helius Webhooks + Geyser-enhanced WS (lowest-latency Solana) · Moralis Streams / QuickNode Streams (generic EVM) | this is the real cost line; profile construction *requires* trade-level data |
| Holders, funding clusters, deployer history | Bitquery / Moralis / Birdeye (x402 metered at **$0.003/request** — the honest COGS anchor) · Dune for batch studies | 50k tokens/day × 10 requests ≈ $1,500/day — budget deliberately |
| Pool/tick liquidity distribution | Uniswap `slot0()`/`ticks()` via RPC; Meteora bin API + DLMM SDK | needed for fee-share estimation in LP planning |
| Social velocity | TinyFish `agent run` on a curated account watchlist (see §5) + X API pay-per-read ($0.005/post) for targeted keyword pulls | ✓ |
| **Arc (chain 5042)** | GetBlock JSON-RPC, The Graph `arc`, Uniswap SDK `ChainId.ARC = 5042` | **No DexScreener/GeckoTerminal/Birdeye/Moralis/Codex coverage.** Self-index or skip |

**Consequence for Arc:** for the launch on 2026-09-16 there is no indexed analytics surface at all
while ~274 tokens and a wave of day-one venues (edgeX FX perps, OpenSea, LI.FI, plus the Arc
launchpads: Tolly, WARP, DYOR, basedpad, ACTFUN, Archemist, Synthra, TowerExchange) go live. A small
indexer over GetBlock RPC producing token pages + first-ever Arc base rates is a *defensible first
mover wedge* on a chain with an unusual audience — and the same engine is what §2 needs on Solana.
Sequence: Solana for the strategy/backtest, Arc for the land grab, one shared schema.

---

## 4. Monetization (numbers from research, not wishes)

**Reference points:**
- Per-trade standard: 0.9-1.0%; a user trading $10k/month already pays $90-100/month. That is the
  realistic ceiling for a subscription that does not execute, and it is a worse headline than "1%".
- Analytics subscription bands: $49-69/mo mainstream (Nansen Pro, DeFiLlama Pro) · $150-1,350/mo pro/API
  (LunarCrush, DeFiLlama API, Kaito from $833/mo). **Self-serve band to target: $29-99/mo, desktop tier $199-499.**
- Affiliation: Axiom pays referrers **30% of net fees** — the primary acquisition engine in this niche.
  Budget 25-30% of net revenue out the door.
- Execution: Jupiter integrator fees keep **80%** (Jupiter takes 20%).
- Ads/sponsorship: DexScreener token ads **from $299** and a **$100k-minimum** product; newsletter
  $250-500/placement at 10k subs; KOL posts $200-5,000 (nano-micro); display CPM $3-10 vs KOL CPM $20-100
  — **native/KOL inventory is worth 5-20× banner inventory**.
- Scale reality check (DefiLlama, fetched 2026-09-10): Axiom Pro annualized $364M fees / $214M revenue;
  GMGN $209M fees; Trojan $20M; Photon's 30-day fees $682k — market share rotates violently. The
  winner-take-most axis is execution speed and affiliate reach, not features. **Do not compete on speed.**

**Model order (each stage funds the next):**

1. **Free scorecard** with a public, versioned, miss-publishing base rate. This *is* the marketing and
   the moat: it costs nothing to distribute and cannot be copied without doing the work.
2. **Subscription $29-99/mo** for planner + LP simulator + journal + portfolio view. Positioned as
   "the thing you use before and after the trade", never against the 1% fee.
3. **Affiliate 25-30%** of net subscription revenue, from day one; assume it in the model.
4. **Sponsored placement inside launchpad/DEX surfaces**, sold as *classified* inventory: paid items
   are labeled AND the paid-share is published as part of the social metric. Sponsorship that cannot
   survive that disclosure is not sold.
5. **Execution integration (optional, later)**: route swaps, take an integrator fee; keeps ~80%.
6. **Token: deferred, deliberately.** Precedents: KAITO -73% from launch and its demand loop (Yaps)
   killed · BMT far below launch · ARKM -97% from ATH (with buybacks). Meanwhile the fee-capture
   products (Axiom, GMGN, Photon) mostly never launched one. A fee-share or buyback token also pulls
   the product toward MiFID/financial-instrument classification in the EU (MiCA full enforcement since
   2026-07-01) and carries the classic US investment-contract fact pattern. The product's only real
   asset is trust in the score; a token converts that asset into a liability. Revisit only after
   revenue exists and with counsel.

---

## 5. Social volume: what TinyFish can and cannot do

Measured this session, not assumed:

| Attempt | Result |
|---|---|
| `tinyfish fetch content get "https://x.com/search?q=...&f=live"` | **fails** — 302 to a login wall, 0 posts |
| `tinyfish fetch content get "https://x.com/<user>/status/<id>"` | `page_not_found` |
| `tinyfish agent run --url "https://x.com/<profile>" "extract 5 recent posts as JSON"` | **works logged-out**: COMPLETED in ~41s, returns `text`, relative `date` ("11h", "Sep 9"), `replies`, `reposts`, `likes`. No absolute timestamps, no impressions, no author-per-item, no reply threads. LLM-extracted, so counts are best-effort, not an API contract. |

**Verdict:** TinyFish is the right tool for **profile-scoped social velocity** across a curated
watchlist (30-80 accounts per chain: launchpads, KOLs, the token's own community), refreshed on a
schedule — no API key, no per-read fee. It is the wrong tool for a keyword firehose (blocked) and
unacceptable for accounting-grade engagement. For keyword streams (e.g. every mention of a ticker in
the last hour), budget the official X API at $0.005/post: monitoring 100 candidate tokens × 20 posts
= $10.

What the app computes from it: unique authors/hour · author concentration · velocity change ·
**paid-share** (boosted placement + accounts funded from the deployer cluster) · cross-platform
confirmation against Telegram/Discord growth. Never a standalone entry signal.

---

## 6. Distribution

1. Referral revenue share (the observed primary engine; Axiom's 30% is the benchmark).
2. The published scorecard as content: every token page is a long-tail query ("is X a scam", "X score",
   "X token analysis") and the page is generated by the product — the one channel where this product
   structurally outranks a terminal.
3. X threads publishing hit-rate stats and misses; Telegram/Discord presence where the audience already
   lives (Telegram bots historically out-distributed web apps in this niche).
4. KOL/affiliate deals at $500-5,000/post for mid-tier, with performance terms.
5. Points program **only if the rules can be published** (Axiom's points→token conversion is still
   unconfirmed; pre-token points programs are now the default demand-capture tool).

## 7. Structural risks

| Risk | Mitigation |
|---|---|
| Sponsor conflict with an honest score | classify paid placement and publish the share; refuse sponsors that require score changes |
| Free-with-fee competitors (0.9-1% per trade) undercut a subscription | never compete on execution; sell the pre/post-trade layer |
| Arc has no indexer coverage at launch | that is the wedge, but it is also a cost: budget self-indexing |
| Data COGS creep ($0.003/request metered) | score only tokens that pass cheap prefilters; cache aggressively; batch on-chain reads |
| Wash trading (17% of trades, up to 10× graduation inflation) and survivorship bias (62%/yr) | de-wash volume before scoring; always include dead tokens in base rates |
| Regulatory | no token, no yield promises, no financial advice framing; publish methodology |
