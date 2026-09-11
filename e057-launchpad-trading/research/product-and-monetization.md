# Product and monetization research — launchpad token scoring + strategy/LP planning web app

Research date: 2026-09-10 (all fetches run this session; page dates cited where the source published one).
Method: `tinyfish search` + `tinyfish fetch content get` on pricing/docs pages. ~30 external pages consulted.
Confidence legend: **H** = read directly on a first-party page or reproduced in two independent sources; **M** = one credible secondary source or first-party page with visible inconsistencies; **L** = snippet-only, third-party blog, or internally contradictory — treat as direction, not number.

Currency: USD unless noted. "Fee" below means the platform's own per-trade cut, exclusive of gas/priority fees and slippage.

---

## Competitor table

### A. Consumer trading interfaces / terminals (the direct audience overlap)

| Product | What it does | Pricing model | LP range planning | Strategy automation | Confidence |
|---|---|---|---|---|---|
| **Axiom** (axiom.trade) | Solana/onchain terminal: one-click buy/sell, limit orders, wallet tracking, Twitter monitor, migration tools, perps, points program | Per-trade only. Base ~1%; "Net Fee 0.95%, Cashback 0.05%" at Bronze (2X) tier; referral codes advertise 10–20% fee discounts. No subscription | No | Partial: limit orders, no ladder/TP-rule engine, no journal | **H** on fee + referral docs; **M** on tier mechanics |
| **GMGN** (gmgn.ai) | Multi-chain (SOL/BSC/Base/ETH) meme discovery + trading, copy-trading, holder tracking, wallet analytics, Telegram bot | Per-trade only. Docs state flat 1% handling fee, "no additional charges", no monthly subscription | No | Copy-trading (follow wallets), no laddering/rules engine | **H** on 1% + no subscription |
| **Photon** (photon-sol) | Solana web/mobile terminal, fast execution | Per-trade only, ~1% per buy and sell; no subscription | No | Limit orders; no plan/journal layer | **M** (review sites agree on 1%; Photon does not publish a fixed platform fee page) |
| **BullX** (bullx.io) | Multi-chain trading terminal, "Neo" UX, sniping, copy-trading | Per-trade only, 1% per buy/sell; 0.9% when signed up via referral link | No | Copy-trading; no rules engine | **M** (docs say 1%, affiliates advertise 0.9%) |
| **Trojan** (trojan.com) | Telegram trading bot on Solana | Per-trade only, 1%, 0.9% via referral; hierarchical referral tree with volume thresholds | No | Sniper/copy-trade only | **H** |
| **Padre → Terminal** (padreapp.com) | Multi-chain terminal (SOL/ETH/Base/BNB), ~300ms execution | Per-trade, plus "up to 35% of your trading fees back automatically" as a retention rebate | No | Copy-trading; no planning/journal | **M** (rebate claim is first-party marketing) |
| **DexScreener** | Free DEX charting/aggregation at scale; monetizes token promotion | Free to users. Ads: token advertising "from $299"; enhanced token info $299; trending-bar product. Docs also describe a fixed product with a **$100,000 minimum budget** (B2B-facing) | No | None (watchlists/alerts only) | **H** on $299 entry and $100k min existing; **L** on the exact 10k/25k/50k/100k impression ladder ($299/$699/$999/$1,999) |
| **GeckoTerminal** | Free DEX tracker across 100+ chains, free public API | Free; monetized indirectly through CoinGecko API subscriptions | No | None | **H** |
| **Birdeye (crypto UI)** | Free-ish DEX analytics ("Trenches", trackers, supercharts) + data API | Data side: free tier ~30K compute units/mo; x402 pay-per-request at **$0.003/request** with all endpoints, no subscription | No | None | **M** on x402 pricing and free tier |
| **Metaora / DeFi LP tools** (Meteora DLMM, Revert Finance, Arrakis) | Concentrated-liquidity position builders, auto-rebalancing vaults, LP analytics; Meteora runs "referral staking" paying referrers **up to 8% of fees from LPs** | Vault/manager fees + LP fee share; Meteora app free, protocol fees parameterized per pool | **Yes** — this is the only part of the market that actually does range planning | Auto-rebalance vaults, but not "plan + journal" for the user | **M** (Meteora referral-staking number from a secondary news source, 2026-07-20) |

**Read on this table:** every consumer terminal monetizes the same way — ~0.9–1.0% per trade, no subscription, with a fee discount as the acquisition hook and a revenue-share rebate as the affiliate hook. Nobody in this row sells a subscription, and nobody in this row does plan-and-review tooling.

### B. Analytics / data providers (adjacent, mostly dev- or pro-facing)

| Product | What it does | Price | LP planning | Strategy automation | Confidence |
|---|---|---|---|---|---|
| **Nansen** | Onchain wallet labels, smart-money flows, token dashboards | Free tier + Pro at **$49/mo annual, $69/mo monthly**; API credits $10 per 10,000 credits. Third-party sources cite legacy "Pioneer" at $99–129/mo and a $1,299/mo tier — contradicts the first-party docs | No | Alerts only | **M** (first-party docs page is the best source; third-party numbers conflict) |
| **Arkham** | Entity attribution, Intel Exchange (bounties on addresses), exchange | Free intel; Intel Exchange fees ~2.5% maker / ~5% taker on bounties/payouts | No | Bounties, no trading rules | **M** |
| **Bubblemaps** | Wallet-cluster / insider-distribution visualization, BMT token | Free (token-gated perks) | No | No | **H** on token/prod; **L** on perk specifics |
| **Kaito** | Attention/mindshare analytics, KOL scoring, Yapper leaderboards, "Attention Markets" | Studio/Pro subscriptions **from $833/mo billed annually** per the sales page; Kaito also ran a Yapper subscription at 0.2 SOL for top leaderboard users | No | No | **H** on $833/mo entry (first-party pricing page); **M** on Yapper sub gates |
| **LunarCrush** | Social volume/sentiment across 20k+ assets, API, MCP | Pricing page shows **Hobby free, Individual $5/day, Builder $15/day, Scale $45/day** (≈$150/$450/$1,350 per month). Secondary sources list $90/$300/$900/mo, and older press cites $72–90/mo — the page appears to have been repriced toward usage-based daily billing | No | No | **M** (first-party page read; earlier published numbers conflict) |
| **DeFiLlama** | TVL/fees/revenue/volume aggregator | Free tier; **Pro ~$49/mo** (page shows $40.83/mo effective, docs say $49/mo or $490/yr); **API $300/mo or $3,000/yr**; Enterprise custom | No | No | **M** (page vs docs differ slightly) |
| **TradingView** | Charting, alerts, Pine scripting, crypto data | Basic free; Essential $14.95/mo; Plus quoted $29.95–34.95/mo; Premium quoted $59.95–69.95/mo across sources; annual billing cuts ~15% | No (not LP-aware) | Yes: Pine strategies, alerts, webhooks — the strongest generic automation layer in the set | **M** (per-tier price varies by source and by crypto vs non-pro bundle) |
| **Moralis** | Dev API: wallet, token, NFT, price, DeFi, Streams | Starter **$149/mo** annual; Pro **$249/mo** (comparison table on the same page shows $199); Business **$749/mo** (table shows $490) | No | No | **M** — the pricing page contradicts itself; use as a band, not a number |
| **CoinGecko API** | Price/market/onchain data API | Demo free; paid tiers from ~$35/mo, "starting from $103.20/mo billed annually" per one comparison | No | No | **M** |
| **Mobula** | DeFi pool price/market data API | Free 10k req, Start-up 125k, Growth 1.25M, Enterprise unlimited — **prices are not published on the pricing page** | No | No | **L** on price (undisclosed) |
| **Birdeye (reputation SaaS)** | Unrelated CRM/reputation product that dominates "Birdeye pricing" search results at $299–349/mo/location | — | — | — | **H** as a search-pollution warning, not a competitor |

---

## Pricing benchmarks

**What consumers already pay per trade (the price anchor for any execution feature):**
- 0.9–1.0% per trade is the industry standard across Axiom, GMGN, Photon, BullX, Trojan, Padre. Confidence **H**.
- Discount mechanics: 10% off with a referral code (Axiom, GMGN), 0.9% vs 1% (Trojan/BullX), cashback tiers reducing net fee to 0.95% (Axiom), up to 35% fee rebate (Padre). Confidence **H/M**.
- Implication: a user trading $10k/month already pays $90–100/month in platform fees. That is the realistic ceiling for any subscription that does not also execute trades — and it is a *worse* headline number than "1% per trade" because it is visible and monthly.

**What pros pay for analytics subscriptions:**
- Low end: Nansen Pro $49–69/mo; DeFiLlama Pro $49/mo. Confidence **M/H**.
- Mid: LunarCrush Individual ≈$150/mo at current daily billing; DeFiLlama API $300/mo. Confidence **M**.
- High end: Kaito from $833/mo; LunarCrush Scale ≈$1,350/mo; Nansen legacy tiers reported up to $1,299/mo. Confidence **M**.
- Realistic self-serve band for a new analytics product: **$29–99/month**, with a $199–499/mo pro tier for desks. This is inferred, not sourced. Confidence **L** (inference).

**Dev-facing data cost (COGS, not revenue):**
- Free tiers everywhere (Birdeye 30K CU, Mobula 10k req, CoinGecko demo, DeFiLlama open API) make a zero-marginal-cost prototype possible.
- Paid dev tiers: Moralis $149–749/mo; CoinGecko ~$35–103+/mo; DeFiLlama API $300/mo; Birdeye x402 at $0.003/request (metered, no commitment). Confidence **M**.
- For a scoring product, per-request metering (x402-style) is the honest COGS model: score N tokens × M endpoints.

**Advertising / sponsorship benchmarks:**
- DexScreener token advertising: from **$299**, with a $100k-minimum product existing for larger buyers. Confidence **H** on entry, **L** on the impression ladder.
- Newsletter placements: Paved benchmarks put 10,000 subscribers at **$250–500 per placement**; finance/B2B lists quote **$70–180 per 1,000 opens**; tech-newsletter CPMs $40–60, top niche $80–150. Confidence **M** (vendor blogs).
- Crypto KOL per-post rates: nano $200–1,500; micro $500–5,000; up to $200,000 for top accounts; effective crypto-KOL CPM **$20–100**. Confidence **M** (agency reports, self-interested but mutually consistent).
- Crypto display/banner CPM is low: ~$3–10 average, versus $20–100 for KOL posts — i.e. **native/KOL inventory is worth 5–20x banner inventory** in this niche. Confidence **M**.
- Conflict flag: the natural sponsors of a launchpad-token scoring product are launchpads and DEXes — the parties whose tokens will dominate the "bad" bucket of any honest score. Confidence **H** (logical, not sourced).

---

## Revenue mechanics with numbers

**1. Interface / aggregator fees — the money in this niche**
- Direct-to-user platform fee of 1% on both buys and sells, taken from the input amount before execution (BullX docs explicitly state this). Confidence **H**.
- Aggregator-level: Jupiter's Ultra Swap API lets integrators attach fees, but integrator fees require a Referral Program account and **Jupiter takes 20% of that fee**. Jupiter's own base fee is often quoted around 0.1%. Confidence **M** — this is the single most important number if the app routes swaps: a third-party app attaching 1% on top keeps 0.8%.
- Scale evidence (DefiLlama protocol pages, fetched this session — trailing/annualized figures, they move daily):
  - GMGN: $46.74M fees with an annualized rate stated as $209.26M in fees / $167.52M in revenue. Confidence **M** — DefiLlama's revenue definition for such apps is not transparent.
  - Axiom Pro: annualized $364.31M fees / $214.05M revenue. Confidence **M**.
  - Photon: $682,170 in fees over a trailing 30-day window on the page. Confidence **M** — note this is ~1–2 orders of magnitude below its peak, i.e. terminal market share rotates violently.
  - Trojan: annualized $20.31M fees / $14.27M revenue. Confidence **M**.
  - TokenTerminal all-time fee ranks from a snippet: Flashbots $1.2B, GMGN $259.7M, Trojan $223.8M, BullX $206.2M, bloXroute $204.5M. Confidence **L** (snippet).
- Take-away: a 1% interface fee on memecoin volume is a nine-figure business for the top two or three products and a low-eight-figure business for the rest. The distribution is winner-take-most, driven by execution speed and affiliate reach, not features.

**2. Referral / affiliate programs**
- **Axiom: referrers earn 30% of Axiom's net fee on every trade made by their Level 1 referrals.** Confidence **H** (first-party referral docs, dated 2026-06-12).
- Trojan: hierarchical referral tree, users must trade above a volume threshold (~$10k) to earn; fee drops 1% → 0.9% for referred users. Confidence **M**.
- GMGN: partner/rebate program where higher invited volume yields higher rebates; user-side codes advertise 10–20% fee discounts. Confidence **M**.
- Meteora: referral staking launched 2026-07-20, referrers earn **up to 8% of fees from LPs**, and it drew 65M MET in the first four days. Confidence **M**.
- Launchpad-side referral payout sample: launchpad.meme publishes 15% of *platform fees* (not volume) per referral, verified-trade accounting. Confidence **M** — small player, but it shows the 15–30% band.
- Believe splits trade fees 50/50 with the token creator. Confidence **M**.
- pump.fun: creator fee sharing across up to 10 wallets (announced 2026-01), then the ability to redirect creator fees entirely; graduated tokens pay creators up to 0.95%. Confidence **M**.
- Exchange affiliate baseline: 30–50% revenue share is standard; Coinbase pays 50% of referred users' trading fees for the first 3 months then a lower rate. Confidence **M**.
- **Economic consequence for the concept:** if the app's growth is affiliate-driven, expect 20–35% of net revenue to leave as referral payouts before any other cost. A scoring app that routes trades through Jupiter at 1% keeps ~0.8% gross and then owes ~0.24–0.28% to its referrers.

**3. Trading-bot fee models**
- Purely variable: success-only per-trade fee, no subscription, failed transactions not charged (Trojan, BullX, GMGN). Confidence **H**.
- Retention rebates instead of subscriptions: cashback tiers (Axiom), automatic fee rebates (Padre up to 35%). Confidence **M**.
- There is essentially **no precedent for a pure-subscription trading product in this niche**. The closest analogues are analytics desks (Nansen, Kaito, LunarCrush) which sit beside the trade flow rather than inside it.

**4. Subscription benchmarks (crypto analytics)**
- $49–69/mo is the mainstream individual price (Nansen Pro, DeFiLlama Pro). $150–1,350/mo is the pro/API band (LunarCrush, DeFiLlama API, Kaito). Confidence **M**.
- Nobody in this niche successfully charges a subscription *for trading signals for brand-new tokens*; the closest thing is copy-trading, which is free and monetized via the 1% execution fee.

---

## Token models and outcomes

| Product | Token | Utility at launch | Outcome as of 2026-09-10 | Confidence |
|---|---|---|---|---|
| **Kaito** | KAITO | Attention/mindshare token; staking (sKAITO) to distribute Yapper rewards; Studio/Markets access | Launched Feb 2025 at $1.12, spiked above $2.00, now ~$0.30 → ~73% below launch and ~85% below the peak. Yaps (the program that created the token's demand loop) was **shut down in January 2026**; the team pivoted to Kaito Studio and Attention Markets | **M** (prices from CMC/CoinGecko snippets; shutdown + pivot from CoinGecko's 2026 guide) |
| **Bubblemaps** | BMT | Analytics access/perks on a free product | Launched 2025-03-11 with 1B supply; trading ~$0.017 today with ~$21M 24h volume on one source and ~$98k on another (venue-level discrepancy, **L**) — far below launch | **M** on launch + current price; **L** on volume |
| **Arkham** | ARKM | Intel Exchange bounties/auctions (fee-bearing), platform currency | Launched on Binance Launchpad at $0.05, ATH $3.98, now ~$0.098 → ~-97.5% from ATH but ~+96% over launch price; ~88% drawdown cited ahead of a Sept 2026 unlock. Buybacks using $5.6M of SOL reported | **M** |
| **Axiom** | none (points only) | Points program exists; **no token conversion or claim confirmed as of 2026-08-12** | Points program as pre-token retention tool | **M** |
| **Nansen, Photon, BullX, Trojan, GMGN, DexScreener** | none (verified) | — | Note: "GMGN" tokens appear on Coinbase/price sites at sub-cent valuations — these are almost certainly third-party memecoins, not a platform token. Do not treat as a real token model | **M** (absence verified for Axiom/Padre; **L** for GMGN token legitimacy) |

**Industry pattern (2026):**
- Token buybacks are the dominant "value accrual" narrative: crypto projects spent **~$638–640M on buybacks in 2026**, up ~17% year over year, but concentrated — reports say two projects did ~90% of it. Confidence **M** (FT, 2026-08-30; secondary coverage 2026-08-31).
- Attention/analytics tokens have performed badly versus their launches even when the product retained users (KAITO, BMT). The tokens whose products capture a **per-trade fee** have mostly avoided launching tokens at all — they don't need to, because the cash flow is already there.

**Regulatory framing for a fee-sharing or buyback token (high level):**
- **EU / MiCA**: fully enforceable since 2026-07-01, with the transitional grandfathering window closed; CASPs need authorization across the EU. A token that promises a share of platform revenue or systematic buybacks is much more likely to be assessed as a financial instrument under MiFID than a plain utility token, which pulls in prospectus and licensing obligations. Confidence **M** on MiCA timeline; **L** on how any specific fee-share design would be classified — that is a legal determination, not a research finding.
- **US**: a revenue-share token is the classic fact pattern regulators have treated as an investment contract; enforcement posture in 2026 is materially looser than 2023–24 but the statutory test is unchanged, so a fee-share token still implies registration risk and most teams structure as "utility + discretionary buyback" to hedge. Confidence **L** — no primary 2026 US source was reviewed in this pass; treat as directional only.
- **Sanctions/geoblocking**: any token distribution or bounty payout must handle OFAC/EU-sanctioned jurisdictions and wallet screening, and Intel-Exchange-style payouts (Arkham: ~2.5% maker / ~5% taker) show the compliance cost is already being priced into these products. Confidence **M** on the fee numbers, **L** on the compliance generalization.
- Practical read for this product: **do not launch a fee-sharing token in year one.** The precedents (KAITO, BMT, ARKM) are negative, the legal surface is the largest single item on the roadmap, and the product's actual competitive advantage (honest scoring) is the thing a token most easily corrupts.

---

## Distribution playbook

**How the incumbents actually acquire users, in order of observed impact:**

1. **Referral revenue share (the primary engine).** Axiom gives referrers 30% of net fees; Trojan runs a hierarchical referral tree; Meteora pays up to 8% of LP fees and drew 65M MET in four days from it; GMGN runs tiered partner rebates. Combined with user-side discounts (10–20% off), referral is simultaneously acquisition and the retention loop. Confidence **H** on Axiom's 30%; **M** on the rest.
2. **Points programs as pre-token demand capture.** Axiom runs points with no confirmed token conversion; this is now the default way to buy volume in advance of a TGE. Confidence **M**.
3. **KOL and affiliate deals on X.** Micro-KOLs at $500–5,000/post with crypto KOL CPMs of $20–100; exchange-style 30–50% revenue share for high-volume affiliates. Confidence **M**.
4. **Community-native distribution**: Telegram bots (Trojan, GMGN bot) and Discord live where the traders already are, which is why Telegram bots have historically out-distributed web apps on Solana. Confidence **M** (structural inference from product mix).
5. **Copy-trading networks**: GMGN, BullX, and Padre all ship copy-trading, which creates a *social* acquisition flywheel (a leader's followers must join the same terminal). Confidence **H** on the feature, **M** on its acquisition weight.
6. **Paid placement inside data surfaces**: DexScreener token ads from $299 and trending-bar inventory; "get trending" boosts are effectively paid acquisition for tokens, and the reciprocal for a tool is to be the thing that *measures* whether a boost worked. Confidence **M**.
7. **SEO/content**: every token has a page and every page is a long-tail query ("is X a scam", "X score"). This is the one channel where a scoring product has a structural advantage over a terminal, because the content is generated by the product itself. Confidence **L** (pattern-based inference, no source).

**Share of growth from referral economics:** no first-party disclosure exists. The observable proxy is the payout rate: when a product is willing to hand 30% of net fees to a referrer, referral is not a channel — it is *the* channel. Confidence **L** on the precise share, **M** on the direction.

**2026 go-to-market shape for a new entrant (synthesis, confidence L):**
- Free scoring/alert tier as top-of-funnel, with a public, versioned scorecard — the auditability *is* the marketing.
- Paid tier for the strategy/journal/LP-planning layer ($29–99/mo), positioned as "the thing you use before and after the trade" rather than competing with the 1% execution fee.
- Optional execution integration (Jupiter integrator fee) as an *additive* rev share, not the core model — remember Jupiter keeps 20%.
- Affiliate program at ~25–30% of net revenue from day one; assume it in the model.
- Distribute through Telegram/Discord communities and X threads with published hit-rate stats; seed with a points program only if you can publish the rules.

---

## Gap analysis

Skeptical, feature-by-feature.

**1. Honest base-rate scoring — the real opening, and also the hardest to monetize.**
The base rate for a brand-new launchpad token is brutal and, crucially, *measurable*: peer-reviewed work reports a pooled graduation rate of **0.198%** (Wilson 95% CI 0.189–0.208%) on a large 2026 sample, described as a 3.18x decline from the **0.63%** measured in Sept–Oct 2025 by an earlier study, while an Aug 2024 analysis claimed a 1.4% graduation rate for its window. Confidence **M** on each number, **H** that the estimates disagree by ~7x because the metric depends on window, chain conditions and definition of "graduated."
- What nobody does: publish a score **with its base rate attached** ("this bucket of 40–60 scores graduated 0.9% of the time over the last 90 days, versus 0.2% for the 0–20 bucket"), versioned, with misses shown. Terminals sell a signal; they do not sell calibration. Confidence **H** on the absence (no competitor page reviewed offers calibration or backtested hit rates).
- Why it's hard: base rates move (0.63% → 0.198% within a year), so calibration must be continuously re-fit and publicly retracted when wrong — which is a *publishing* commitment, not a feature.

**2. LP range planning for tokens that are hours old — the most over-sold "gap" in this brief.**
- It is true that no trading terminal does it: Axiom/GMGN/Photon/BullX/Trojan/Padre are spot terminals; Meteora DLMM's own UI and Revert/Arrakis (EVM-oriented) are the only real range tools in the market. Confidence **H** on the gap.
- It is also true that it barely works for the target asset. A volume profile or horizontal level set built on 2–48 hours of data for a token with a few hundred thousand dollars of liquidity is mostly noise: no statistically meaningful volume-at-price, no tested levels, and a print set dominated by bots and a single bonding-curve migration event. Anyone promising "concentrated-liquidity range planning using volume profile" for brand-new tokens is overfitting. Confidence **H** (statistical reasoning, not sourced).
- Defensible version of the feature: apply range planning to *post-graduation* tokens with ≥2–4 weeks of history and ≥$1M liquidity, and for brand-new tokens show only range **scenarios with explicit impermanent-loss and fee-yield ranges** (e.g., "this 10x-wide range earns X%/day at observed volume, goes out of range in N hours at observed volatility"), labeled as simulation, not plan. Confidence **L** (design recommendation).

**3. Post-trade review / journaling — genuinely empty, genuinely unproven.**
No reviewed competitor ships a per-token journal tying an alert to a plan to the actual fill to a post-mortem. Journals exist as separate tools (spreadsheets, generic trading journals) and terminators explicitly do not do it. Confidence **H** on the absence, **L** on willingness to pay: journaling is a *cost* to the user (time) whose benefit accrues to the user later, and the same audience is already paying 1% per trade for speed. This is the feature most likely to be admired and not bought.

**4. Social-volume attribution without bot noise — the sharpest technical gap, and incumbents have publicly failed at it.**
- Kaito's mindshare algorithm was publicly criticized in mid-2025 for being gamed (AI-generated replies under Smart Followers, coordinated Yap farming) and the team adjusted the algorithm in response; by Jan 2026 Kaito shut down Yaps entirely. Confidence **M** on the backlash and the algorithm change; **M** on the shutdown.
- Independent of Kaito, the launchpad ecosystem itself manufactures social volume commercially: DexScreener sells "trending bar" placements and token ads from $299, and paid KOL posts run $200–5,000 each. So a naive "social volume" signal on a 1-hour-old token is partly a measurement of the token's marketing budget. Confidence **M** on the ad product; **H** on the logical consequence.
- What nobody ships: a **bot-adjusted** social metric that reports the paid/boosted share separately from organic mentions, plus the wallet-level cross-check (do the accounts posting also receive from the same funding cluster?). This is the most defensible technical differentiator in the whole brief, and it requires data nobody else is packaging (funding-graph clustering + paid-placement inventory surfaces). Confidence **L** (opportunity assessment, not sourced).

**5. Strategy automation for new tokens — where incumbents legitimately win.**
TradingView already owns rule-based alerts/strategies/webhooks, and terminals own fast execution. A new entrant's plan layer must be *lighter* than TradingView's (entry ladders, stop-after-migration, time-based take-profit, LP out-of-range rules) and *pre-filled* from the score, or it is a worse TradingView. Confidence **M**.

**6. Structural risks the brief does not address (highest-value skepticism):**
- **Revenue-model mismatch.** The niche is a volume business: 1% per trade, winner-take-most, with referral economics taking 20–35% off the top. A subscription scoring/journal product is competing for the same wallet against a product that is free to use and profitable per trade. If the app does not touch execution, its revenue ceiling is the analytics-subscription band ($49–99/mo self-serve). If it does touch execution, it must win on speed and liquidity routing — the exact axis where incumbents have durable moats. Confidence **M**.
- **Sponsor conflict.** The only sponsors with money in this niche are launchpads, DEXes, and aggregators. A product whose core asset is an honest base rate will, by construction, rate most of its sponsors' inventory as failures. Ad revenue and the scoring product are in direct tension. Confidence **H** (logical).
- **Token-model temptation.** KAITO (-73% from launch, product program killed), BMT, ARKM (-97% from ATH) show attention/analytics tokens do not hold value, while the fee-capture products (Axiom, GMGN, Photon) mostly declined to launch one. Buybacks are the 2026 fashion but concentrated in two large protocols. A token would convert the product's only real asset — trust in the score — into a liability. Confidence **M**.
- **Data-cost creep**: scoring N new tokens/day with cross-chain holder, funding-graph, and social data is per-request metered (Birdeye x402 at $0.003/request is the honest anchor). At 50k tokens/day × 10 requests, that is $1,500/day in COGS before storage. Confidence **L** (arithmetic on a sourced unit price).
- **Definitional risk on "new chains":** permissionless launchpads exist on chains where RPC/indexer coverage is thin, which means the score's input data is least reliable precisely where the product claims its edge. Confidence **L** (unverified in this pass).

**Bottom line for the design doc:** the two genuinely unserved spaces are (a) calibrated, published base-rate scoring and (b) bot-adjusted social attribution; both are publishing/measurement products with unproven willingness to pay. LP range planning and journals are real gaps but weak products for hours-old tokens. The most likely viable shape is a free, auditable scoring surface that drives distribution, with a paid strategy/journal/LP-simulation layer priced at $29–99/mo, and execution routed through a Jupiter-style integrator fee as an optional additive revenue stream — with a token explicitly deferred, not on the roadmap.

---

## Sources

Format: URL — date of source as shown at fetch time (page date or fetch date) — claim taken. All fetched 2026-09-10 unless noted.

**Trading terminals / fees**
- https://docs.axiom.trade — fetched 2026-09-10, page last updated "10 months ago" (≈late 2025) — Axiom product feature list (limit orders, wallet tracking, Twitter monitor, migration tools). Claim: feature set. **H**
- https://docs.axiom.trade (Fees page, via search snippet dated 2025-05-03) — "Net Fee: 0.95%", "Cashback: 0.05%", Bronze (2X) tier — claim: fee/cashback structure. **M**
- https://docs.axiom.trade (Referral Program, dated 2026-06-12) — "You earn 30% of Axiom's net fee on every trade made by your Level 1 referrals." Claim: referral payout. **H**
- https://www.airdroplet.com — dated 2026-08-12 — checked that day: Axiom has a points program, no confirmed token conversion or claim. Claim: no token yet. **M**
- https://docs.gmgn.ai/index/gmgn-fees-settings — fetched 2026-09-10 — "GMGN only charges a 1% handling fee for a single transaction... no additional charges", 0.01 SOL example. Claim: 1% flat, no subscription. **H**
- https://docs.gmgn.ai (Referral Link page, dated 2025-02-13) — partner rebate program, higher invited volume → higher rebate. Claim: referral mechanics. **M**
- https://defillama.com/protocol/gmgn — fetched 2026-09-10 — "$46.74m in fees", annualized "$209.26m in fees and $167.52m in revenue". Claim: revenue scale. **M**
- https://defillama.com (Axiom Pro) — fetched 2026-09-10 — annualized "$364.31m in fees and $214.05m in revenue". Claim: revenue scale. **M**
- https://defillama.com/protocol/photon — fetched 2026-09-10 — "$682,170 in fees" over the displayed 30-day window. Claim: current Photon fee run-rate far below peak. **M**
- https://defillama.com/protocol/trojan — fetched 2026-09-10 — annualized "$20.31m in fees and $14.27m in revenue". Claim: Trojan scale. **M**
- https://tokenterminal.com/explorer/projects/gmgn/metrics/fees — fetched 2026-09-10 via search snippet — all-time fee ranking: Flashbots $1.2B, GMGN $259.7M, Trojan $223.8M, BullX $206.2M, bloXroute $204.5M. Claim: all-time fee scale. **L** (snippet only)
- https://solanatradingbots.com/photon-how-to-use/ — accessed 2026-09-10 — "Photon does not advertise a fixed platform trading fee." Claim: Photon has no published platform fee. **M**
- https://uwuu.ai/blog/photon-review — dated 2026 — "Photon charges 1% per trade (buy and sell)... There's no subscription." Claim: 1%, no subscription. **M**
- https://bullx.gitbook.io (Fees and Gas) — dated 2025-02-16 — "The 1% fee is calculated on the total SOL amount", taken from input. Claim: 1% fee on input. **H**
- https://coin360.com — dated 2024-11-26 — BullX free to use, 0.9% per transaction via referral link. Claim: referral discount. **L** (older)
- https://solanacompass.com/projects/trojan — accessed 2026-09-10 — Trojan charges flat 1% on successful transactions, 0.9% for referred users; failed swaps not charged. Claim: Trojan fee model. **H**
- https://www.gate.com/learn/articles/top-4-solana-trading-bots/2293 — accessed 2026-09-10 — Trojan hierarchical referral system, users trading above ~$10k qualify to earn. Claim: referral thresholds. **M**
- https://padreapp.com/ — accessed 2026-09-10 — "~300ms execution", "Get up to 35% of your trading fees back automatically." Claim: Padre rebate. **M** (first-party marketing)
- https://revert.finance/ — accessed 2026-09-10 — "Actionable analytics, automation, and management tools for liquidity providers... Uniswap, Sushiswap, Curve, Balancer." Claim: LP management tooling exists, EVM-centric. **M**
- https://solanacompass.com/news/meteoras-referral-staking-program-draws-65-million-met-in-its-first-four-days — dated 2026-07-20 (program launch) — "Referrers earn up to 8% of fees from LPs", 65M MET in first four days. Claim: LP referral economics. **M**

**Data surfaces / ads**
- https://marketplace.dexscreener.com — fetched 2026-09-10 — products: Enhanced Token Info, Token Advertising, Trending Bar Advertising. Claim: ad product line. **H**
- https://marketplace.dexscreener.com (Token Advertising listing) — search snippet accessed 2026-09-10 — "Order Now - from $299.00. Pay with crypto." Claim: $299 entry price. **H**
- https://docs.dexscreener.com — dated 2024-11-07 — advertising "Pricing: Fixed, minimum budget of $100,000 USD"; payment via Coinbase Commerce and Stripe. Claim: high-end B2B ad minimum. **M** (older doc)
- https://dune.com (DEX Screener ad revenue dashboard, via search snippet) — accessed 2026-09-10 — Enhanced Token Info $299; Token Advertising 10k views $299 / 25k $699 / 50k $999 / 100k $1,999. Claim: impression ladder. **L** (third-party dashboard snippet)
- https://www.geckoterminal.com — accessed 2026-09-10 — free GeckoTerminal API for onchain market data. Claim: free tier, no paid GeckoTerminal plan. **H**
- https://birdeye.so — dated 2026-04-16 (x402 announcement) — "Price per request, $0.003", "Full REST API access — all endpoints, no subscription needed." Claim: metered data pricing. **M**
- https://bds-support.birdeye.so — dated 2025-05-15 — free tier 30K compute units/month. Claim: free data tier. **M**
- https://docs.birdeye.so/pricing — fetched 2026-09-10 — page returned not-found; no first-party public tier table located. Claim: Birdeye paid tier pricing is unpublished. **M**
- https://docs.mobula.io/pricing — accessed 2026-09-10 — tiers Free (10,000) / Start-up (125,000) / Growth (1,250,000) / Enterprise (Unlimited) with rate limits; no prices shown. Claim: Mobula pricing undisclosed. **L** on price
- https://moralis.com/pricing/ — fetched 2026-09-10 — Starter $149/mo annual, Pro $249/mo (comparison table on same page shows $199), Business $749/mo (table shows $490). Claim: dev API price band; page self-contradicts. **M**
- https://www.coingecko.com/en/api/pricing — accessed 2026-09-10 — free Demo plan plus paid Analyst/Lite/Pro tiers. Claim: tier structure. **M**
- https://www.g2.com/products/coingecko-api/pricing — accessed 2026-09-10 — "starting from $103.20/month when billed annually". Claim: CoinGecko paid entry. **M**
- https://docs.llama.fi — dated 2026-02-13 — "Pro ($49/month or $490/year)", "API ($300/month or $3,000/year)". Claim: DeFiLlama pricing. **M**
- https://defillama.com/pro — accessed 2026-09-10 — Free $0/month; Pro $40.83/month with 7-day trial. Claim: DeFiLlama Pro price on page. **M** (page vs docs differ)
- https://www.tradingview.com/subscriptions/ — accessed 2026-09-10 — plan structure Essential/Plus/Premium (prices rendered client-side; taken from secondary sources). Claim: plan names. **M**
- https://supa.is — dated 2026-03-04 — Essential $14.95 / Plus $29.95 / Premium $59.95 (2026). Claim: TradingView tier prices. **M**
- https://friendofthetrend.com — dated 2026-06-06 — Essential $14.95 / Plus $34.95 / Premium $69.95. Claim: conflicting tier prices. **M**

**Analytics / social**
- https://docs.nansen.ai — dated "7 days ago" at fetch (≈2026-09-03) — "Subscription: $49/month (annual) or $69/month (monthly)", API credits $10 per 10,000. Claim: Nansen Pro pricing. **M**
- https://academy.nansen.ai — accessed 2026-09-10 — "There are currently only two plans: Pro and Free"; no Enterprise plan. Claim: plan inventory. **M**
- https://nftevening.com — dated 2026-08-20 — Nansen Pro $69/mo or $49/mo annual ($588/yr). Claim: corroborates Nansen Pro. **M**
- https://chainplay.gg — accessed 2026-09-10 — "Pioneer Plan Price: $129/month or $99/month for annual"; also cites $1,299/month tier. Claim: conflicting legacy Nansen tiers. **L**
- https://pro.kaito.ai/pricing — accessed 2026-09-10 — "$833/month billed annually." Claim: Kaito Pro entry price. **H**
- https://www.coingecko.com/learn/what-is-kaito-earn-yap-points — dated 2026-05-07 — "Subscription pricing starts at $833/month"; Kaito shut down Yaps in January 2026, pivoting to Kaito Studio and Attention Markets. Claim: price + Yaps shutdown/pivot. **M**
- https://beincrypto.com — dated 2025-06-17 — Kaito adjusted its mindshare algorithm after backlash over manipulated engagement and low-quality content. Claim: gaming criticism. **M**
- https://www.bitget.com — dated 2025-06-16 — critics argue influencers and projects gamed the Kaito system to inflate visibility. Claim: gaming criticism. **M**
- https://oakresearch.io — dated 2025-03-18 — "Yap farming" via AI-generated replies under Smart Followers' tweets. Claim: specific manipulation vector. **M**
- https://coinmarketcap.com / https://www.coingecko.com — accessed 2026-09-10 — KAITO ≈$0.299 (down ~9.7% on the day); KAITO began trading at $1.12 and rose to ~$2 in Feb 2025 (Yahoo Finance, 2025-02-24). Claim: KAITO outcome. **M**
- https://lunarcrush.com/pricing — fetched 2026-09-10 — Hobby free; Individual "$5/day"; Builder "$15/day"; Scale "$45/day"; all include MCP access. Claim: current LunarCrush pricing. **M**
- https://lunarcrush.com/support — accessed 2026-09-10 — "Individual ($90/mo), Builder ($300/mo), Scale ($900/mo)" — contradicts the current pricing page. Claim: pricing inconsistency. **M**
- https://www.binance.com/en/academy/articles/what-is-bubblemaps-bmt — accessed 2026-09-10 — BMT is the native utility token, 1B supply, launched 2025-03-11. Claim: BMT facts. **M**
- https://www.coingecko.com/en/coins/bubblemaps — accessed 2026-09-10 — BMT ≈$0.01724, 24h volume ≈$21.2M. Claim: BMT current price. **M**
- https://www.kucoin.com/price/BMT — accessed 2026-09-10 — BMT $0.01712 with 24h volume $98,126 — venue-level discrepancy vs CoinGecko. Claim: volume discrepancy. **L**
- https://coinspot.io — dated 2026-03-12 — Arkham Intel Exchange fees: maker ~2.5% on posted bounties, taker ~5% on payouts and auction wins. Claim: Intel Exchange take rate. **M**
- https://en.wikipedia.org/wiki/Arkham_(cryptocurrency_exchange) — accessed 2026-09-10 — ARKM launched on Binance Launchpad at $0.05 and reached $3.98. Claim: ARKM launch/ATH. **M**
- https://www.coingecko.com — accessed 2026-09-10 — ARKM ≈$0.0977. Claim: ARKM current price. **M**
- https://info.arkm.com — accessed 2026-09-10 — "strategic buyback of its own token using $5.6M SOL", prior buyback moved value ~15%. Claim: ARKM buyback. **L**
- https://coinmarketcap.com/cmc-ai/arkham/latest-updates/ — accessed 2026-09-10 — Sept 2026 unlock framed as the biggest price factor; ~88% drawdown cited. Claim: drawdown/unlock. **M**

**Tokens / regulation / benchmarks**
- https://www.ft.com — dated 2026-08-30 — crypto groups spent almost $640M buying back their own tokens in 2026. Claim: buyback volume. **M**
- https://memeburn.com — dated ≈2026-09-02 ("8 days ago") — ~$638M on buybacks in 2026, two projects did ~90%. Claim: buyback concentration. **M**
- https://keyrock.com (Designing Token Buybacks report) — accessed 2026-09-10 — "Tokenholder revenue is up 5x since 2024, yet buybacks remain broken." Claim: buyback efficacy critique. **M**
- https://www.esma.europa.eu (MiCA) — dated 2025-11-28 — MiCA institutes uniform EU market rules for crypto-assets. Claim: MiCA framework. **H**
- https://aminagroup.com — dated 2026-07-01 — "MiCA's transitional period closed on July 1, 2026." Claim: grandfathering end date. **M**
- https://sumsub.com — dated 2026-01-13 — MiCA reshaped EU crypto regulation; what changed ahead of full enforcement. Claim: MiCA enforcement context. **M**
- https://www.researchgate.net — dated 2026-07-07 — pooled pump.fun graduation rate 0.198% (Wilson 95% CI 0.189–0.208%), a 3.18x decline from the 0.63% rate reported for Sept–Oct (earlier study). Claim: base rate for new tokens. **M**
- https://www.binance.com — dated 2024-08-18 — "The real data of pump.fun: 1.4% graduation rate, only 3%..." and a deployer who created 3,357 tokens with 16 graduating. Claim: earlier, higher base rate. **L** (older, exchange blog)
- https://www.cryptopolitan.com — dated 2026-01-29 — pump.fun graduations rose above 1% of daily launches, a six-month high. Claim: base rate is regime-dependent. **M**
- https://pump.fun (Fees page) — dated 2026-05-20 — creator receives a portion of total fees on every trade; creator fee applies to all coins. Claim: creator-fee mechanics. **M**
- https://phemex.com — dated 2026-01-11 — pump.fun creator fee sharing across 10 wallets, with ownership transfer and revoke options. Claim: fee-sharing rollout. **M**
- https://smithii.io — accessed 2026-09-10 — since 2025-09-03, creators of graduated tokens can earn up to 0.95% (3x vs ungraduated). Claim: graduated creator fee rate. **M**
- https://phemex.com — dated 2025-10-30 — Believe charges a small trade fee split 50/50 with the token creator. Claim: Believe split. **M**
- https://dev.to — dated 2026-01-12 — Bags.fm: claim your 1% trading fees anytime. Claim: Bags creator fee. **L**
- https://bags.fm (Terms of Service) — dated 2026-02-11 — Bags may allow users to earn "Bags Points" via a referral program. Claim: Bags referral structure. **M**
- https://defillama.com/protocol/launch-coin-on-believe — accessed 2026-09-10 — shows a "Referral fees" revenue line. Claim: Believe has an on-chain referral fee line. **M**
- https://launchpad.meme/referral-program — accessed 2026-09-10 — "Default rate 15% of platform fees, not trade volume. Accounting basis: verified trades." Claim: launchpad referral payout band. **M**
- https://dev.jup.ag (Add Integrator Fees) — accessed 2026-09-10 — integrator fees require Referral Program accounts; "Jupiter takes 20% of..." the fee. Claim: aggregator take rate. **M**
- https://nansen.ai — dated 2025-06-24 — "Jupiter itself charges a small fee (typically 0.1%) on transactions." Claim: Jupiter base fee. **L**
- https://changehero.io/blog/best-crypto-affiliate-programs/ — accessed 2026-09-10 — affiliates earn up to 50% of trading fees generated by referred users. Claim: exchange affiliate band. **M**
- https://wundertrading.com/journal/en/best-crypto-affiliate-programs — accessed 2026-09-10 — 30–50% commission on trading fees across exchanges; up to 50% revenue share. Claim: affiliate band. **M**
- https://medium.com/crypto/make-money-without-trading-10-crypto-exchange-affiliate-programs... — accessed 2026-09-10 — Coinbase pays 50% of referred users' trading fees for 3 months, then a lower rate. Claim: Coinbase terms. **M**
- https://www.paved.com/blog/newsletter-sponsorship-rates/ — dated 2026 (Jul) — 3,000 subs ≈$75–150/placement; 10,000 ≈$250–500/placement. Claim: newsletter benchmark. **M**
- https://newsletrix.com/blog/newsletter-sponsorship-rates-by-niche — dated 2026 — B2B SaaS $90–180 per 1,000 opens, finance $70–130, creator/lifestyle $25–55. Claim: niche CPMs. **M**
- https://tool.teamzlab.com/creator/newsletter-sponsorship-calculator/ — accessed 2026-09-10 — tech newsletter CPMs $40–60 standard, top-tier $80–150. Claim: CPM band. **M**
- https://disence.com/articles/how-much-does-kol-marketing-cost-in-web3-2026-budget-guide — dated 2026 — crypto KOL rates $200–$200K+; $1,000–2,000 per X post in mid-tier; $500–5,000 per campaign. Claim: KOL pricing. **M**
- https://www.apcollective.io/blog/average-cpms-of-crypto-kols — dated 2026 — typical $1,000–5,000 per post, 8,000–50,000 impressions, effective CPM $20–100. Claim: KOL CPM. **M**
- https://www.luvkaizen.com/blogs/crypto-kol-rate-report-2026 — dated 2026 — nano $200–1,500 per post, micro $500–5,000, up to $200,000 for top accounts. Claim: KOL tier rates. **M**
- https://www.digitalapplied.com/blog/display-advertising-benchmarks-2026-data-points — accessed 2026-09-10 — average display CPM ~$3.12, retargeting to $24.50. Claim: display CPM baseline. **M**
- https://coinzilla.com/blog/why-digital-advertising-still-runs-on-cpm/ — accessed 2026-09-10 — display CPM generally $3–10. Claim: display CPM range. **M**

**Not verifiable in this pass (explicitly marked):**
- Mobula per-tier prices (page lists quotas only).
- Birdeye Data pay-as-you-go vs subscription tier prices beyond the $0.003/request rate.
- Exact DexScreener impression-ladder pricing (only a third-party Dune dashboard snippet).
- Whether any San Francisco/DC regulator has published 2026 guidance specifically on fee-share/analytics tokens — no primary US source was gathered; the US regulatory statement in "Token models and outcomes" is directional only.
- Any first-party disclosure of referral's share of user acquisition for any competitor.
