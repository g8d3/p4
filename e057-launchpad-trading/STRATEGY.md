# Launchpad Token Trading + LP System

Design doc, v1 — 2026-09-10. Chain-agnostic by design; Arc is the first deployment target only
after mainnet (2026-09-16) proves a concentrated-liquidity venue exists.

Evidence base: [`research/base-rates-and-data.md`](research/base-rates-and-data.md),
[`research/lp-strategies-and-math.md`](research/lp-strategies-and-math.md),
[`research/product-and-monetization.md`](research/product-and-monetization.md).
Machine-checked math: [`research/bid-ladder-math.py`](research/bid-ladder-math.py).

---

## 0. The starting premise, corrected

The original idea: *"open concentrated LPs with a range from -50% to -95% below ATH across ~15
tokens, because deep-drawdown tokens have a good chance of bouncing."*

Three things are wrong with it as stated, and all three are load-bearing.

**1. A bid-side LP cannot profit from a bounce — upside is capped at exactly par.**
A range placed entirely below spot is funded in quote and mechanically converts to the risky token
as price falls through it (Uniswap v3/v4 range order, Meteora Bid-Ask). Consequences, derived:

```
L            = C / (√pb - √pa)
average fill = √(pa · pb)                    <- geometric mean of the bounds
V(p)         = C                             for p >= pb   (all quote, 0 tokens)
V(p)         = Xmax · p                      for p <= pa   (all risky, 0 quote)
IL vs cash   = V(p) - C = -L(√pb - √p)²/√pb  <= 0
full-fill drawdown vs cash = 1 - √(pa/pb)
```

For `-50% / -95%` of ATH: average entry `-84.2%`, full-fill value `-68.4%` vs cash, and if the price
returns to `-50%` you hold exactly `C` in quote and zero tokens. **The round trip captures no price
gain, only fees.** It is synthetically a short put: premium = fees, notional = the token's trip to
zero. To turn a bounce into profit you must withdraw near the trough and hold/sell outside the AMM,
or run an ask-side range above — which is a different, directional strategy.

**2. Fees cannot pay for a completed fill.** One full downward traversal of a `pa/pb = 0.10` range
returns `≈ f × C` at a 1% fee tier, against `0.684 × C` of mark-to-market loss vs cash. You need
~68 full traversals per fill to break even on the inventory. Fee APR shown by venues belongs to the
active bin, not to a bid-side rung parked 80% below spot.

**3. "Down 50% from ATH" is not "cheap."** A launchpad ATH is usually a minutes-long spike. `-50%`
from that spike is routinely 2-20× the migration price. The ladder's *first* fill is priced off a
statistic with almost no information content.

What survives from the original idea: **the bid ladder is an excellent entry/accumulation
mechanism** — it gives a known average cost (`√(pa·pb)`), it earns fees while it fills, and it
enforces pre-committed tranches. It is a *buying* tool, not a *bounce-capture* tool. That is how it
is used below (S4).

---

## 1. Base rates (the prior everything else is judged against)

| Fact | Value | Source |
|---|---|---|
| pump.fun tokens whose last trade is launch day | 68.7% (18.67M token cohort) | CoinGecko 2026-06 |
| pump.fun tokens dead within 2 days | >80% | same |
| pump.fun tokens surviving >90 days | 4.55% (~850k) | same |
| Graduation rate, by regime | 1.4% (2024) → 0.63% (Sep–Oct 2025) → 0.198% pooled (2026) → 0.26% weekly avg (2026) | 4 studies, disagree ~7× |
| 4.meme (BNB) graduation | ~1.34% of 384k created | single secondary source, low confidence |
| Create-side concentration | top 1% of creator address groups = 58.6% of all 15.2M coins | arXiv 2609.10246 |
| Wash trading | 17% of all pump.fun trades; can inflate graduation odds up to 10× | same |
| Meme sector, Jan 2025–Feb 2026 | equal-weighted top-10 meme basket `-78.74%` | SSRN (Krause) |
| Survivorship bias | equal-weighted crypto indices overstate returns by 62.19%/yr | Stoeckl 2026 |

**Not documented, and this is the whole edge:** no public dataset answers *"after -50%/-80%/-95% from
ATH, what fraction recovers +50%/+100%/10×, over what horizon"*. Only anecdotes exist. Every
strategy below therefore ships with the base-rate measurement attached — the strategies are
hypotheses until the app produces that table (see §6).

---

## 2. Architecture: levels decide *where*, volume decides *how much*, base rate decides *whether*

Four inputs, one order of operations. A token is only traded if it passes §3; the levels in §4 place
the orders; the volume profile in §5 sizes them; §6 measures whether it worked.

### 2.1 Horizontal levels (pure price geometry, computable from candles)

| Level class | Definition | Use |
|---|---|---|
| ATH fractions | `ATH × {1.0, 0.5, 0.25, 0.1, 0.05}` | take-profit plane, drawdown buckets for base rates |
| Volume nodes | POC = max-volume price bin; HVN = local maxima; LVN = local minima, from §5 | entries on HVN retest, targets into LVN gaps |
| Value area | `[VA_low, VA_high]` = shortest price range holding 70% of traded volume | the "is this token still alive" band |
| Consolidation ranges | runs of ≥6h with price σ below the token's median σ and volume above median | supply/demand shelves; strongest horizontal levels |
| Round numbers + tick size | powers of 10, 2×, 5× multiples; USD integers | order clustering, quoting offset |

Level strength score `Si` = volume traded within ±1σ of the level × number of touches × (1 / age decay).

### 2.2 Trading rules (buy / sell / cut)

**BUY — three entries, all pre-committed:**

- **B1 Reclaim (momentum).** Price closes above an HVN or a consolidation-range top *after* having
  spent ≥6h below it, with volume on the reclaim ≥1.5× the trailing 24h median. Entry at the
  reclaim close. Stop below the level (`level × (1 - 1.5σ_1h)`). Rationale: the *only* documented
  graduation-predictive signal class is speed/quality of liquidity accumulation, and wash trading
  (17% of trades) poisons raw volume — so require the retest/reclaim shape, not volume alone.
- **B2 Deep-value tranche (the disciplined version of the original idea).** Requires: drawdown
  `≤ 0.2 × ATH`, token still passes §3 safety, and *two* consecutive higher lows on ≥4h bars with
  volume decay (capitulation exhaustion), and social velocity rising off a low base with a
  paid-share below 50% (§7). Enter in 3 tranches at `-85% / -92% / -96%` of ATH or at HVNs there,
  whichever is deeper. This is where a bid-side LP ladder is deployed (S4).
- **B3 Post-migration dip.** Within 72h of bonding-curve graduation / first real pool, buy the first
  reclaim of the migration price after a ≥50% drawdown from the post-migration high. Stop at the
  migration price. Highest historical edge class for "being early", per the accession-premium
  evidence (Robinhood-chain cohort: 754 wallets took 93.2% of supply before public access).

**Positions are never averaged down beyond the pre-committed tranches.** Adding a 4th tranche is a
new decision requiring a new B2 qualification, not a reaction to a loss.

**SELL — scale out on the level grid, never "when it feels right":**

| Trigger | Action |
|---|---|
| `+50%` from average entry | sell 1/3 |
| price reaches the next HVN above, or `0.5 × ATH`, whichever is first | sell 1/3 |
| runner | trailing stop at `max(2σ_4h, 25%)` below the highest close |
| any ATH-fraction level reached on a Sunday-thin book | accelerate: sell 1/2 of remaining |

**CUT — four independent kill switches, any one fires, all of them mechanical:**

1. **Price stop.** B1: below the reclaimed level. B2: `-50%` from average entry. B3: below migration price.
2. **Thesis stop (checked hourly, from on-chain data):** LP unlocked/removed >20% · mint/freeze
   authority still live · deployer or top-10 wallet moved >5% of supply to an exchange/market ·
   holder count declining for 12h · 24h volume < `$25k` or < `5%` of the token's own 7-day median.
3. **Time stop.** 7 days with no higher low → exit at market whatever the price. Dead tokens do not
   come back on a schedule; the 4.55% >90-day survival rate is the prior.
4. **Portfolio stop.** Venture bucket drawdown `> 40%` → stop opening new positions for 7 days.

### 2.3 Portfolio construction and sizing

| Parameter | Value | Reason |
|---|---|---|
| Venture bucket | 5-10% of trading capital | terminal-zero rate ≥ 95% of the token population |
| Max concurrent positions | 15 | the original idea's number, kept, but as a *dispersion cap*, not a safety claim |
| Max per token | 1/15 of the bucket, i.e. 0.33-0.67% of capital | so one rug costs <1% of the book |
| Max per token in B2 | 2/15 | deep-value tranche needs room for 3 entries |
| Correlated positions | treat all launchpad tokens on one chain within one 24h window as ONE position for the bucket cap | cohort correlation is unmeasured but the common factor is obvious |
| LP-routed share of a token's budget | ≤ 50% (only the rungs below the deepest level you believe in) | LP adds out-of-range risk without adding upside |

**Diversification is dispersion, not protection.** Splitting across 15 tokens does not change
expected value; launchpad cohorts are launched, pumped and dumped on the same cycle, so the 15
positions will fill and die *together*. This is the reason the bucket is capped in percentage terms
rather than relying on the coin count.

---

## 3. Universe filter (checks that must pass before any order)

Hard fail on any of: mint/freeze authority live · LP not burned or locked · top-10 holders > 35%
excluding LP/burn · deployer in the serial-launcher cluster and its prior tokens' median outcome
below zero · token age < 6h · liquidity < `$150k` (post-migration) or < `$50k` (B2 deep-value) ·
volume/liquidity ratio < 0.5 (dead) or > 200 (wash-dominated) · copycat name/symbol of an existing
token · any pool whose deployer retained > 5% (creator pre-graduation dumps are structurally
incentivized by the curve→AMM switch).

Soft-score (0-100, published with its base rate, never as a bare number): liquidity growth per
trade (the strongest documented graduation predictor, arXiv 2602.14860) · unique-holder growth ·
buy/sell balance · organic-volume share after wash removal · social velocity with paid-share
discount · deployer history · holder distribution shape.

---

## 4. LP allocation algorithm (the actual answer to "put liquidity per volume profile and levels")

Inputs: `ATH`, spot `P`, volume-at-price histogram `H(p)` (from §5), `σ_d` (realized daily vol),
pool liquidity `L_pool`, fee tier `f`, token budget `C_tok` (≤ 2/15 of bucket), kill level `P_kill`.

1. **Value area.** Compute `POC`, `VA_low`, `VA_high` (70% of volume).
2. **Candidate levels** below `P` and above `P_kill`: ATH fractions `{0.5, 0.25, 0.1, 0.05}` ∪ HVNs
   ∪ consolidation-range tops. Snap each to the nearest HVN within `±1σ_d`.
3. **Rung weights.** `w_i ∝ H(level_i) × (1 - distance_penalty)` where
   `distance_penalty = (P - level_i) / P` clipped to 0.5. Normalize. Cap any single rung at 40% of
   `C_tok`. *Volume at a price is the only honest evidence that someone will buy there again* —
   that is why the weights are volume densities and not equally spaced.
4. **Rungs.** `[pa_i, pb_i] = [level_i·(1-kσ), level_i·(1+kσ)]`, `k = 0.5-1.0`, non-overlapping,
   `pb_1 = min(0.95·P, nearest level above)`. Convert each rung's width to ticks/bins at the venue's
   spacing (`tick = log(P)/log(1.0001)` on v3; bin id `= ln(P)/ln(1+bin_step/1e4)` on DLMM).
5. **Venue choice per rung.** Concentrated-liquidity venue available and `f ≥ 0.3%` → bid-side LP
   rung (earns fees while filling). Otherwise → spot limit orders (full-range V2 pools have no
   bid-side primitive; four.meme reverted new pools to PancakeSwap V2 in 2025-03). Never place a
   bid-side rung on a pool where you would not also be happy to own the token at that price with no
   fees at all.
6. **Full-fill accounting.** Σ rung budgets = planned position size; average entry = capital-weighted
   *harmonic* mean of the per-rung geometric means, `√(pa_i·pb_i)`. Report it *before* entering —
   this is the number that decides whether the trade makes sense.
7. **Exit plane.** On reclaim of `VA_high`: withdraw all LP rungs, convert to spot (this is the
   mandatory step that captures the bounce the LP itself cannot). Then run the §2.2 SELL grid.
   If `-50%` below the deepest rung or `P_kill` is touched: withdraw everything, market-exit, no
   rebalancing into lower rungs. **Rebalancing a ladder downward is how this strategy dies** — every
   iteration converts more quote into a token in a possibly terminal downtrend.
8. **Instrument choice.** If the thesis is *upside* (B1/B3), use spot or an unbounded-upper range
   `[pa, ∞)`, whose value `L(2√P − √pa)` grows without bound (sublinearly, ~√P). A bounded range is
   for income on tokens you already own, never for directional upside.

Worked example (`C=100k`, `ATH=1.00`, range `[0.05, 0.50]`, uniform liquidity):

| price ×ATH | % below ATH | capital deployed | tokens | value | vs cash |
|---|---|---|---|---|---|
| 0.500 | 50.0% | 0.0% | 0 | 100,000 | 0.0% |
| 0.300 | 70.0% | 33.0% | 85,114 | 92,570 | -7.4% |
| **0.2166** | **78.3%** | **50.0%** | 151,949 | 82,906 | -17.1% |
| 0.100 | 90.0% | 80.8% | 361,544 | 55,311 | -44.7% |
| 0.050 | 95.0% | 100.0% | **632,456** | **31,623** | **-68.4%** |
| 0.000 | 100% | 100.0% | 632,456 | 0 | -100% |

Half the capital is committed only after a 78.3% drawdown, and capital density is *highest* at the
bottom (`dY/dp = L/(2√p)`: 3.16× denser at 0.05 than at 0.50). "The deep part of the range protects
you" is backwards; the deep part is where the money actually goes.

---

## 5. Volume profile for DEX tokens (must be built; nobody sells it)

No vendor computes volume-at-price for DEX tokens — TradingView-style profiles exist only for
CEX-listed instruments. Construction from trade-level data:

1. Ingest swaps (pool address, price, quote amount, timestamp) for the token's entire life.
2. Bucket by **log price** (K bins, e.g. 100-200 between all-time low and ATH), accumulate quote volume.
3. Compute `POC` (max bin), `VA_high`/`VA_low` (70% of volume), HVN/LVN via local extrema on the histogram.
4. Time-decay (half-life 7-14 days) for a "recent profile" and keep the full-life profile as reference.
5. Normalize to get `H(p)` for §4 step 3.

Data path, cheapest first: GeckoTerminal trades endpoint (~10 req/min, free) for spot checks →
Bitquery (real-time streams, Four.meme API includes bonding-curve progress) or Helius/Geyser for
continuous Solana coverage → self-indexed RPC for chains no aggregator covers (Arc). Note the honest
constraint: for a token with 2-48h of history and a few hundred thousand dollars of liquidity, the
profile is mostly bot prints and one migration event. **Volume-profile sizing is only defensible on
tokens with ≥2-4 weeks of history and ≥$1M liquidity.** Below that, the app shows *simulation with
explicit IL and fee ranges*, labeled as a scenario, not a plan.

---

## 6. What must be measured before this is trusted (the experiment backlog)

The three gaps below are also the product's moat — nobody has this data.

| # | Question | Data needed | Why it matures into the product |
|---|---|---|---|
| G1 | Rebound base rate per drawdown bucket: after `-50/-80/-95%` from ATH, what fraction recovers `+50%/+100%/+10×`, in what time, and what is the terminal-zero rate per bucket? | full price/volume history for a launchpad cohort (10k+ tokens, one chain) | the published, versioned scorecard nobody has |
| G2 | Intra-cohort correlation: do 15 simultaneous launchpad positions fill and die together? Measure the common factor. | same cohort, synchronised | decides whether 15 positions is diversification or leverage |
| G3 | Bid-side ladder backtest: time-above-range, volume crossed inside each rung, fee capture net of other LPs and JIT, inventory at exit, vs a "hold quote" benchmark | swap-level data + pool liquidity history | the LP planner's expected-value engine |

Method notes that are non-negotiable: include dead tokens (survivorship bias is 62%/yr equal-weighted)
· de-wash the volume (17% of trades) · report hit rate *and* payoff ratio *and* max drawdown, since
the payoff distribution is fat-tailed by construction · publish misses.

Infrastructure already in this repo to reuse: `e025-hyperliquid-candle-tails/` (backtest/event-study
harnesses), `e021-hyperliquid-playground/` (data ingestion + SQL), `e035-trading-video-alerts/`
(proximity-to-level detection, already does S/R alerts).

---

## 7. Social volume (what to measure and what it is worth)

Social volume is a *timing and liveness* input, never a quality input, and it is contaminated by
purchased inventory (DexScreener trending placements from $299; paid KOL posts $200-5,000 each).

Signals, in order of signal-to-noise: unique authors per hour (not raw mentions) · author-quality
concentration (is it 3 accounts posting 90% of it?) · velocity change (2nd derivative) · **paid-share**:
fraction of the volume traceable to boosted placement or to accounts that received wallet funding
from the same cluster as the deployer · cross-platform confirmation (Telegram/Discord member growth
against X mentions) · reply sentiment only after bot filtering.

Use: B2 requires social velocity rising *off a low base* with paid-share < 50% (organic re-discovery,
not a marketing push); the SELL grid accelerates when social volume peaks together with price
(peak attention = distribution). Never use social volume as an entry signal on its own — Kaito's
mindshare algorithm is the cautionary precedent: it was gamed until the program behind it (Yaps) was
shut down in January 2026, and KAITO is ~73% below launch.

Feasibility, measured not assumed (details in `research/base-rates-and-data.md` §Social volume):

| Source | Verdict |
|---|---|
| Official X API | pay-per-read **$0.005/post**; no free tier. Fine for targeted keyword pulls (200 posts = $1), wrong for a firehose. |
| TinyFish `fetch` on `x.com/search` | **does not work**: 302 to a login wall, zero posts. |
| TinyFish `fetch` on `x.com/<user>/status/<id>` | `page_not_found`. |
| TinyFish `agent run` on an `x.com/<profile>` | **works**: ~41s/run, returns `text`, relative `date`, `replies`, `reposts`, `likes`. No absolute timestamps, no impressions, LLM-extracted counts. Good enough to rank social velocity across a 30-80 account watchlist; not accounting-grade. |
| LunarCrush | listed Individual/Builder/Scale at $5/$15/$45 per day |
| Kaito / TweetScout / Cookie3 / Elfa / Santiment | pricing unverified — do not plan on them without a second check |

---

## 8. Deployment order

1. **Now → Arc mainnet (any day before 2026-09-16):** nothing on Arc. Arc has no production
   concentrated-liquidity venue (Synthra is testnet), ACTFUN graduates tokens into a constant-product
   AMM with no bid-side primitive, and no aggregator indexes chain 5042 (GetBlock RPC and The Graph
   `arc` do). A whole-chain analytics/launchpad data gap is itself the opportunity — see `APP.md`.
2. **First real deployment: Solana / Meteora DLMM** — the only venue where the bid-side ladder is
   native (`StrategyType.BidAsk`, `maxBinId = activeBinId - 1`, `@meteora-ag/dlmm` v1.9.x), with the
   deepest launchpad pipeline, and where the SDK + bin API make the §4 algorithm executable.
3. **Second: Base / Aerodrome Slipstream** (v3-style concentrated positions with gauges), then
   Uniswap v3/v4 anywhere EVM.
4. **Arc:** re-evaluate after mainnet, when Synthra/ACTFUN/TowerExchange/RadarDEX publish LP
   mechanics and an indexer exists. Expect an institutional, stablecoin-denominated economy rather
   than a degen launchpad economy — the base-rate profile there may be *better* than Solana's, which
   is exactly the thing to measure first instead of assuming.

Paper-trade each strategy at G1-G3 scale before capital: the expected value of S2/S4 is unknown
because the rebound base rate is unknown. That is not a reason to skip it; it is the reason step 1
is measurement.
