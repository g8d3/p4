# Bid-side concentrated-liquidity LP on launchpad tokens: mechanics and honest risk profile

Scope: evaluation of the proposal "open a concentrated LP position with a range from about -50% to -95% below ATH, split capital across ~15 launchpad tokens, betting on mean reversion". All formulas are derived from the primary protocol specs cited in **Sources**; no numbers are invented. Confidence is marked per claim: **[H]** high, **[M]** medium, **[L]** low.

As-of date for all "current" statements: **2026-09-10**. Note: the proposal's "Arc chain ID 5042" is incorrect; Arc testnet is **5042002** and Arc mainnet is scheduled for **2026-09-16** (see Venue feasibility).

---

## Mechanics of bid-side CLMM

### 1. Uniswap v3 / v4 range order (the canonical primitive)

Pool convention: token0 = risky launchpad token, token1 = quote (USDC/SOL/ETH). Spot price `P = token1 per token0`, `√P` is the pool's stored sqrt price. A position has bounds `p_a < p_b` (token1 per token0), with `√p_a`, `√p_b` the corresponding sqrt bounds. Ticks satisfy `P = 1.0001^i` and `√P = 1.0001^(i/2)`; standard tick spacing is 10 / 60 / 200 for the 0.05% / 0.30% / 1.00% fee tiers. **[H]** (Uniswap math primer part 2; Uniswap fees concept page.)

**A position placed entirely below spot (`P > p_b`) is a "range order" / limit-buy.** Uniswap documents exactly this: the price space *below* spot is denominated in the lower-priced (quote) asset, so a below-spot position must be funded with quote and is "swapped for [the risky token] when the spot price of [the risky token] drops past" the range. Uniswap also states that buy-**stop** and stop-**loss** orders are *not* expressible as range orders, because they would need the wrong asset on the wrong side of spot. **[H]** (Uniswap "Understanding Range Orders".)

**Holdings.** For a position with liquidity `L` (the sqrt-reserve invariant variable) and current sqrt price `√p`:

```
amount0 = L * (√p_b - √p) / (√p * √p_b)      [in range]
amount1 = L * (√p - √p_a)                    [in range]

amount0 = L * (√p_b - √p_a) / (√p_a * √p_b)  if √p <= √p_a   (fully filled, all risky)
amount1 = 0
amount0 = 0
amount1 = L * (√p_b - √p_a)                  if √p >= √p_b   (not filled, all quote)
```

with inverse forms `L = x·(√p·√p_b)/(√p_b−√p) = y/(√p−√p_a)` and the invariant `(x + L/√p_b)(y + L·√p_a) = L²`. **[H]** (Uniswap math primer part 2, formulas quoted verbatim in notation `p_l, p_u, p'`.)

**Bid-side specifics (derived from the formulas above, all algebra shown):**

- Initial capital, all in quote, when spot `P ≥ p_b`: `C = L·(√p_b − √p_a)`. → **`L = C / (√p_b − √p_a)`**.
- Quote spent to reach price `p ∈ [p_a,p_b]`: `C_spent(p) = L·(√p_b − √p)`. **Fraction of capital deployed: `(√p_b − √p)/(√p_b − √p_a)`** — linear in *sqrt* price, not in price.
- Risky tokens held at `p`: `X(p) = L·(1/√p − 1/√p_b)`. Maximum (at `p ≤ p_a`): **`X_max = L·(1/√p_a − 1/√p_b)`**.
- **Average entry price of the fraction filled between `p_b` and any `p` is `√(p·p_b)`** (proof: `C_spent/X = L(√p_b−√p)/(L(√p_b−√p)/(√p·√p_b)) = √p·√p_b`). Full-range average entry: **`√(p_a·p_b)`** (the *geometric mean* of the bounds, not the arithmetic mean).
- Position value in quote: `V(p) = L·(2√p − p/√p_b − √p_a)` for `p∈[p_a,p_b]`; `V(p)=C` for `p ≥ p_b`; `V(p)=X_max·p` for `p ≤ p_a`.
- **IL versus holding quote (cash), bid-side case: `V(p) − C = −L·(√p_b − √p)²/√p_b ≤ 0`, with equality only at `p = p_b`.** At the bottom of the range the drawdown versus cash is **`1 − √(p_a/p_b)` of the capital**. **[H] (derived; consistent with the published v3 holdings formulas.)**
- **Upside is capped at exactly 0 relative to cash**: for any `p ≥ p_b`, `V = C`. There is no state of the world (excluding fees) in which a purely bid-side range position is worth more quote than it started with. It is synthetically a **short put**: premium = fees, downside = the token's price to zero.
- **Price → zero (residual inventory).** Below `p_a` the position is 100% risky token, `X_max = L·(1/√p_a − 1/√p_b)` units, and **zero quote remains**. `p_a` does not stop the loss; it only stops further buying. If the token goes to 0 the residual inventory is worth 0 and the loss is 100% of the capital converted. The only ways to keep residual quote are (a) set `p_a` above the price you believe is a floor, (b) split capital into multiple disjoint ranges so only one rung is filled at a time, or (c) never let the range fill.
- **Rebound behaviour.** Composition is a pure function of current price (path-independent). A rebound from the trough back to `p_b` restores the position to `C` worth of quote and 0 tokens — the AMM mechanically sells back everything it bought, at the same prices, so the round trip captures **no price gain**, only fees. To convert a bounce into realized profit above `C`, you must either (i) withdraw the tokens while the price is near the trough and sell/hold them outside the AMM, or (ii) place an ask-side range above to sell into the bounce. Leaving the position alone caps you at par. **[H, derived].**
- **Unfilled-order risk.** Uniswap explicitly states a range order "will be **unfilled** if the spot price crosses the given range and then reverses to recross in the opposite direction before the target asset is withdrawn", and that you must monitor or use a manager to withdraw on fill. **[H]** (Uniswap range orders doc.)

**When fees are earned.** Only while the position overlaps the *active* tick/bin. Above the range: zero fee accrual, forever, until price falls in. Fees are tracked per-position via fee-growth accumulators:

```
tokensOwed = L * (feeGrowthInside_current − feeGrowthInsideLast) / 2^128
```

(fee growth is in the token's smallest unit per unit of `L`, per token). Fees are paid in both tokens; for a *downward* traversal the swap input is the risky token, so the fee is collected in the falling token and its quote value erodes if the fall continues. **[H]** for the fee-growth formula (Uniswap math primer part 2 "Calculating uncollected fees"), **[M]** for the directional denomination nuance.

**Fee-versus-inventory arithmetic (single-LP upper bound).** If you are the only liquidity in the range, a full traversal of `[p_a,p_b]` pays a fee equal to `f × X_max` tokens (down move) or `f × L(√p_b−√p_a) = f × C` quote (up move), where `f` is the fee tier. Valued at the average fill price `√(p_a p_b)` this is `≈ f × C`. Against that, the mark-to-market drawdown at the bottom versus cash is `(1 − √(p_a/p_b))·C`. For the proposed range (`p_a/p_b = 0.10`) that ratio is `f / (1 − √0.10) = f / 0.6838`; at `f = 1%` a full traversal recovers only ~1.5% of the drawdown — you would need on the order of 68 full range traversals at a 1% fee to offset one completed fill. **[H] for the algebra, [M] for the "sole LP" assumption** (in reality you share fees with other LPs in the bins and with JIT liquidity).

**Capital-intensity profile (derived).** With uniform `L`, dollars deployed per unit of price are `dY/dp = L/(2√p)`, i.e. the ladder is **densest at the bottom**: for the worked example, 4,625 quote per 0.01 of price at `p=0.05` versus 1,462 at `p=0.50` (×3.16). This is the opposite intuition to "the deep part of the range protects you": most of the capital is committed in the deepest, most-likely-to-be-worthless bands.

**Multi-rung ladders change the shape.** Splitting the same capital into several disjoint bid-side ranges with equal capital each lowers the average entry (the overall average entry is the capital-weighted *harmonic* mean of each rung's geometric-mean entry) but concentrates more capital at the deepest prices. Worked numbers in the next section. **[H] (derived).**

### 2. Meteora DLMM (Solana)

DLMM discretises price into **bins** of width `bin_step` basis points: `P_i = (1 + bin_step/10,000)^i`. Inside a bin the invariant is constant-sum, `L = P·x + y`, so swaps inside the active bin have zero slippage: `out_Y = ⌊in_X·P⌋`, `out_X = ⌊in_Y/P⌋`. Bins sit in arrays of 70, and a `PositionV2` can hold up to 1,400 bins; `bin_step` tops out at 400 bps. **[H]** (Meteora "DLMM Formulas", "What is DLMM".)

- **Bid-side support is native.** The docs define the **Bid-Ask** shape as "an inverse Curve distribution with more liquidity near the edges", and the canonical DCA use case is: "Deposit quote token single-sided and use Bid-Ask or selected bins below the current price. As price moves down, your quote token can gradually convert into the base token." **[H]** (Meteora "DLMM Strategies and Use Cases".)
- **Limit-order pool mode.** A DLMM pool can be created with a limit-order function mode (program-visible as a distinct pool/`concreteFunctionType`), where liquidity deposited into bins behaves as limit orders, and fees are collected in the input token (single-sided fee) per a pool-level "Collect Fee Mode" setting. Practical effect: a bid-side limit-order position accrues fees *in the token that is being sold into it*. **[M]** (Meteora docs: collect-fee-mode; Meteora `dlmm_config.jsonc` mentions `concreteFunctionType: 0` for limit-order pools; not all details verified in contract source here.)
- **Dynamic fees.** `total fee = min(base + variable, 10%)`; `base = base_factor × bin_step × 10 × 10^base_fee_power_factor` (1e9 precision); `variable = ceil(variable_fee_control × (volatility_accumulator × bin_step)² / 1e11)`, with the volatility accumulator driven by recent bin movement. Protocol share ≤ 25% of the trading fee. So during dumps the fee is *higher* than baseline — partial, not full, compensation for the adverse selection of being the buyer on the way down. **[H]** (Meteora "DLMM Formulas"; protocol-share max 2,500 bps.)
- **The bid-side bin ladder is not a uniform-dollar DCA either.** Bid-Ask puts *more* capital at the two extremes of the selected range; a "selected bins below price" deposit puts it wherever you choose. As with v3, fee accrual is per crossed bin and is exactly zero until the price reaches your bins. Meteora's own docs warn: Bid-Ask "may sit away from the active price until the market moves into the edge bins", and that DLMM strategies "do not remove impermanent loss or out-of-range risk". **[H]** (Meteora strategies doc.)
- Mechanics are otherwise isomorphic to v3: crossing your whole bin ladder leaves you 100% in the risky token; the ladder stops buying at the bottom bin; fees stop when out of range. **[H]**.

### 3. Uniswap v4 hooks, and other native "buy-the-dip ladder" venues

- **v4 CL math is identical to v3** ("The liquidity math in Uniswap v4 is the same as v3"), and range orders "have the same implementation in both Uniswap v3 and v4". So the v4 core adds no new bid-side primitive. **[H]** (Uniswap math primer part 2; Uniswap range orders doc.)
- What v4 adds is **automation via hooks**: there are working examples of **limit-order hooks** (place order at a tick/direction; tokens held by the hook; `afterSwap` detects the price crossing the target and fills). A custom "laddered bid-side" hook is therefore implementable, but it is custom code you own and must audit — Uniswap/OpenZeppelin both flag that hooks that call `modifyLiquidity` own the liquidity and carry extra accounting/security burden. **[H]** for the hook examples; **[M]** for the practical maturity.
- **Maverick AMM** is the clearest *native* directional-LP design found: besides Static mode it exposes movement modes; its "Mode Right" "tracks the price of the base asset as it declines, keeping the bottom of the price range at the current price" — i.e. a native bid-side accumulation mode rather than a static range. **[M]** (docs.mav.xyz "Liquidity Strategies", 2024-07-22; CoinMarketCap description).
- Other bins-based designs exist (e.g. Liquidity Book style venues) but were not verified in this pass; treat as unconfirmed.

---

## Worked example (numbers)

Setup: ATH = 1.000 (normalised); proposed range **`p_b = 0.50` (−50% from ATH) to `p_a = 0.05` (−95% from ATH)**; capital `C = 100,000` quote; spot at ATH at entry; uniform liquidity `L` (v3 default, Meteora "Spot" over the same bins).

`√p_a = 0.223607`, `√p_b = 0.707107`, `√p_b − √p_a = 0.483500`
**`L = 100,000 / 0.483500 = 206,825`**
**`X_max = L(1/√p_a − 1/√p_b) = 632,456` tokens**
**Average entry if fully filled = `√(0.05 × 0.50) = 0.158114` (84.2% below ATH)** — vs the arithmetic midpoint of the range, 0.275, and vs the −50% level 0.50.

Capital deployment, inventory and mark-to-market (all values in quote, vs holding 100,000 cash):

| price ×ATH | % below ATH | capital deployed | tokens held | position value | vs cash | avg fill of filled part |
|---|---|---|---|---|---|---|
| 0.500 | 50.0% | 0.0% | 0 | 100,000 | 0.0% | — |
| 0.400 | 60.0% | 15.4% | 34,524 | 98,370 | −1.6% | 0.4472 |
| 0.300 | 70.0% | 33.0% | 85,114 | 92,570 | −7.4% | 0.3873 |
| **0.2166** | **78.3%** | **50.0%** | 151,949 | 82,906 | −17.1% | 0.3291 |
| 0.150 | 85.0% | 66.1% | 241,525 | 70,084 | −29.9% | 0.2739 |
| 0.100 | 90.0% | 80.8% | 361,544 | 55,311 | −44.7% | 0.2236 |
| **0.050** | **95.0%** | **100.0%** | **632,456** | **31,623** | **−68.4%** | **0.1581** |

Readings:

1. **Half the capital only moves after a 78.3% drawdown** (`p* = ((√p_a+√p_b)/2)² = 0.2166`). The 50%→78% drawdown band (0.50 → 0.2166) deploys only half the money; the last 50% is committed between −78% and −95%.
2. **A completed fill is not a −95% loss; it is a −68.4% loss versus cash** (`1 − √(p_a/p_b) = 0.6838`), *provided the token still trades at 5% of ATH*. If the token then goes to zero, the residual 632,456 tokens are worth 0 and the loss is 100% of `C`.
3. **The AMM's ceiling is par.** If the price bounces all the way to 0.50 (or 2× ATH), the position is worth 100,000 quote and 0 tokens. All alpha must come from fees or from being withdrawn into tokens near the trough.
4. **Fee break-even is orders of magnitude away from the drawdown.** At a 1% fee and sole-LP status, one complete downward traversal pays `≈1% of C` in fees (≈1,000 quote at average fill price, ≤3,162 quote valued at the top of the range) against 68,381 quote of mark-to-market loss vs cash at the bottom. Fees only become material if price *oscillates through the range many times*; a single crash-and-die earns almost nothing.
5. **Fee APR shown by venues is not this position's APR.** Venue APRs derive from pool fee/TVL and historical in-range volume (mostly the active bin). A bid-side position sitting below spot has no in-range volume until a crash, and the crash usually arrives as one candle whose fee is a rounding error against the inventory it creates.

**Multi-rung comparison.** Split `C = 100,000` into two equal rungs, `[0.15, 0.50]` and `[0.05, 0.15]` (50,000 each):

- `[0.15,0.50]`: `L = 156,344`; `[0.05,0.15]`: `L = 305,453`.
- Full fill: 182,574 + 577,350 = **759,924 tokens for 100,000 quote → average entry 0.1316** (versus 0.1581 for the single wide range). The combined average entry is the harmonic mean of the rung geometric means: `2/(1/√(0.15·0.50) + 1/√(0.05·0.15)) = 0.1316`.
- But deployment is *slower* early: at price 0.10 the ladder has deployed 71.7% vs 80.8% for the single range, and then dumps its entire second rung between 0.05 and 0.15.

So "ladder the bid side" is a real design lever, but its effect is **a lower average entry bought with more capital in the deepest bands** — i.e. it increases, not decreases, left-tail exposure. It is not a risk reduction.

---

## Risk profile and failure modes

Ranked by destruction potential.

1. **Token goes to zero / rug (dominant term). [H]**. Below `p_a` you hold only the risky token; the terminal value is 0. Launchpad tokens have adversarial supply mechanics (mint authority, freeze authority, deployer holdings, unlocked LP), so the relevant question is not "will it bounce" but "what fraction of the cohort survives at all". Finding a defensible base rate is a prerequisite for this strategy, and it was not established from primary data in this research pass. **[M]**.
2. **"Down 50% from ATH" is not "cheap". [M]**. ATH for a launchpad token is typically a minutes-long spike; −50% from that spike can still be 2–20× the launch/migration price. The strategy's *first* fill price (`p_b`) is set by a statistic (ATH) with almost no information content about value. This is the single most common conceptual error in the proposal.
3. **Strictly capped upside, uncapped downside. [H, derived]**. `V(p) ≤ C` for all `p ≥ p_a` with equality at/above `p_b`. Combined with (1), the payoff is a short put: small premium (fees), full notional loss potential. Any "bounce" upside must be manufactured by active management (withdraw at the trough, re-list an ask-side range, or sell on a DEX), which changes the strategy into a directional trade.
4. **Fees are earned only in range, and the in-range period is the toxic one. [H]**. Zero fees while price is above `p_b` (the normal state for most of the cohort, most of the time). Fees appear exactly while informed sellers are distributing into you — the classic loss-versus-rebalancing (LVR) exposure. Empirically, arbitrage losses exceed fee income in many of the largest Uniswap pools, and v2 full-range pools were more profitable for passive LPs than v3 concentrated pools (Fritsch & Canidio 2024). **[H]**.
5. **Unfilled range order. [H]**. Uniswap's own docs: a range order can be crossed and then reversed before you withdraw, leaving you with fees and no tokens. If the thesis is "own the token after the dip", the primitive does not guarantee delivery.
6. **No stop-loss. [H]**. Uniswap documents that stop-loss orders are not expressible as range orders. The only "stop" is manual withdrawal — which requires monitoring exactly during the fastest, most congested part of a crash.
7. **Rebalance / laddering churn. [M]**. The natural failure path is: price blows through the rung → LP opens a new lower rung with fresh quote → repeat. Each iteration converts more quote into a token with a possibly terminal downtrend, and adds slippage, gas/priority fees and (on Solana) position-account rent (refundable) to the cost base. On Solana tx costs are small (fractions of a cent plus priority fees) so the churn cost is dominated by the inventory loss, not by fees. **[M]**, no measured dataset found.
8. **JIT liquidity / competition for fees. [M]**. Just-in-time LPs can add liquidity immediately before large swaps and remove it immediately after, capturing fees without carrying inventory risk. A standing bid-side position is systematically the slower, adverse-selected liquidity. **[M]** (mechanism well-known; no quantified memecoin-specific measurement found in this pass).
9. **Diversification across ~15 tokens is weaker than it looks. [M/L]**. Splitting does not change expected value, only dispersion. Launchpad cohorts are launched, pumped and dumped on the same market cycle, so the common factor (market beta / sector rotation) dominates the idiosyncratic term: the 15 positions will tend to fill and to die *together*. Quantifying the intra-cohort correlation is an open task for the design doc; no source was found that measures it directly.
10. **Fee denomination drag. [M]**. Bid-side fills pay fees in the input token, which during a dump is the falling token. Fee income in a token that then goes to zero is worthless regardless of the quoted amount.

**Honest one-line summary:** a fully bid-side CLMM range is a limit-buy ladder with a *geometric-mean* average entry (`√(p_a·p_b)`), a hard ceiling of zero PnL versus cash, a floor of −100% if the token dies, and fee income that is provably too small to offset a single completed fill at realistic fee tiers. It is a directional short-volatility position on a token class with a high terminal-zero rate, not a market-neutral yield trade.

---

## Evidence from the field

Verdict up front: **no rigorous public backtest of bid-side CLMM ladders on launchpad tokens was found in this research pass.** The available evidence is (a) protocol documentation of the mechanic and its warnings, (b) adverse-selection academic literature for concentrated liquidity generally, and (c) self-reported operator experience. Weight the three accordingly.

- **Uniswap (first-party):** "allows you to approximate a limit order by providing a single asset as liquidity within a specific range"; range order makers "generate fees while the order is filled"; a range order "will be unfilled if the spot price crosses the given range and then reverses"; stop-loss and buy-stop orders are impossible. **Verdict: mechanic works as designed; the failure modes are documented by the vendor. [H]** (developers.uniswap.org, accessed 2026-09-10).
- **Meteora (first-party):** Bid-Ask is built for DCA entries into volatile assets, and single-sided quote below price is the documented DCA-in pattern; but "DLMM strategies can improve capital efficiency, but they do not remove impermanent loss or out-of-range risk", and Bid-Ask "may sit away from the active price until the market moves into the edge bins" (i.e. no fees until the dump). **Verdict: the venue documents the exact mechanic and its dead zone. [H]** (docs.meteora.ag, accessed 2026-09-10).
- **Fritsch & Canidio, "Measuring Arbitrage Losses and Profitability of AMM Liquidity" (arXiv:2404.05803, v1 2024-04-08, v2 2024-04-22):** arbitrage losses "exceed the fees earned by liquidity providers across many of the largest AMM liquidity pools" and "Uniswap v2 pools are more profitable for passive LPs than their Uniswap v3 counterparts". **Verdict: strong quantitative support that concentrated/passive LP income is routinely beaten by adverse selection. [H]** (caveat: Uniswap pairs, not memecoins).
- **Milionis et al., "Automated Market Making and Loss-Versus-Rebalancing" (arXiv:2208.06046, v1 2022-08-11, v5 2024-05-27):** formalises LVR as the core LP cost from stale prices being picked off by arbitrageurs; the model matches actual LP returns empirically. **Verdict: the theoretical basis for why fills on dumps are negatively selected. [H]**.
- **Heimbach, Schertenleib, Wattenhofer, "Risks and Returns of Uniswap V3 Liquidity Providers" (2022-05-18):** theoretical model of LP choices; the abstract notes that for their studied (normal) pairs v3 positions face "little to no risks of losing money" but "the returns are generally small", and it cites an earlier empirical attempt concluding ~50% of positions lose money. **Verdict: benchmark, not memecoin-specific; useful for the "returns are small" prior. [M]**.
- **Operator self-report (Reddit r/solana, "Automated memecoin farming via Meteora DLMM – 24 hour results", posted ~2025-03):** "My strategy only opens one-sided positions (deposit SOL only) with a wide range to the downside. So it 'only' earns when price drops below entry point - but since memecoins are very volatile, it works out most of the time." ~2 SOL per position; bot-driven (scan/filter/rank, deposit/withdraw via DLMM, swap via Jupiter); PnL shared only as screenshots (not extractable). **Verdict: the strategy is in active live use by at least one operator; the claim of profitability is unverified and the sample is 24h. [L–M]**.
- **Third-party guide (bytwork.com, updated 2026-08-08):** recommends Bid-Ask single-sided entries with ranges around −50% to −90% for memecoins, and claims "losses at the lower boundary are only about 22%", calling it a "protective gold standard". **Verdict: this is the same shape as the proposal, and its risk figure is arithmetically inconsistent with its own range.** For a uniform-liquidity range at −50%/−95% of ATH the mark-to-market loss at the bottom is `1 − √0.10 = 55.3%` relative to *spot* (68.4% relative to the ATH-based bounds used here), trending to 100% if the token dies; a 22% figure corresponds to a much narrower range (≈ `p_a/p_b = 0.61`, e.g. −50% to −70%). Treat the "22%" claim as unreliable. **[M]** for the recommendation existing, **[H]** for the arithmetic refutation.
- **Meteora DLMM dynamic fees as compensation (first-party):** total fee can rise toward a 10% cap in high volatility, which does partly pay the LP for buying into dumps. It changes the fee/IL ratio but cannot change the payoff ceiling or the terminal-zero floor. **[H]** for the mechanism, **[M]** for the net effect.

**What is missing and should be produced before committing capital:** a historical simulation on real launchpad-token price/volume series (Meteora DLMM bin-level or Uniswap v3 tick-level data) computing, per token: time-above-range, volume crossed inside the range, fee capture net of other liquidity in the bins, inventory at exit, and terminal outcome vs a "do nothing" quote benchmark — plus the same across a 15-token cohort to measure correlation and portfolio drawdown.

---

## Tooling and APIs

**Uniswap v3 / v4 (EVM)**

- `NonfungiblePositionManager`: `positions(tokenId)` → `liquidity`, `tickLower`, `tickUpper`, plus `mint`, `increaseLiquidity`, `decreaseLiquidity`, `collect`. Pool `slot0()` → `sqrtPriceX96`; `ticks()` → `liquidityNet` per tick, which is exactly the tick-liquidity distribution needed to plan a range. **[H]**.
- SDKs: `@uniswap/v3-sdk`, `@uniswap/v4-sdk`; v4 splits position management into a `PositionManager` peripheral with permit-based flows. **[M]** (official docs; exact package versions not pinned here).
- Fee tiers: 0.05% / 0.30% / 1.00% standard. **[H]** (Uniswap fees concept page).
- Position/fee accounting formulas to reimplement: holdings (above) and `tokensOwed = L·ΔfeeGrowthInside / 2^128`. **[H]** (math primer part 2).

**Meteora DLMM (Solana)** — the most directly applicable stack for this proposal

- `@meteora-ag/dlmm` (npm, v1.9.10 published ~2026-08; repo `MeteoraAg/dlmm-sdk`), with `@coral-xyz/anchor`, `@solana/web3.js`.
  - `DLMM.create(connection, poolPubkey)` / `createMultiple`; `getActiveBin()` → `binId`, `price`.
  - `initializePositionAndAddLiquidityByStrategy({positionPubKey, user, totalXAmount, totalYAmount, strategy:{minBinId, maxBinId, strategyType}})` with `StrategyType.Spot | BidAsk | Curve`, plus `autoFillYByStrategy(...)`. A bid-side ladder is literally `maxBinId = activeBinId - 1` (or a chosen offset) with `totalYAmount` quote and `StrategyType.BidAsk`/`Spot`; `minBinId`/`maxBinId` set the rung.
  - Pool discovery: `https://dlmm-api.meteora.ag/pair/all`. Rust SDK also published; docs claim both TS and Rust SDKs. **[H]** (npm README, accessed 2026-09-10; docs.meteora.ag get-started).
  - Limit-order pools additionally expose a limit-order pool type (`concreteFunctionType: 0`) and a collect-fee mode determining which token fees are paid in. **[M]**.

**Uniswap v4 automation**

- Limit-order hooks exist as reference implementations (Solidity-by-Example "Uniswap V4 Limit Order": `placeLimitOrder(tick, direction)`, hook custody of tokens, `afterSwap` fill detection, `getHookPermissions()`). Building a *laddered* bid-side manager means writing and auditing custom hook code, and anything that calls `PoolManager.modifyLiquidity` owns that liquidity (OpenZeppelin warning). **[H]** for the pattern, **[M]** for production readiness.

**Managed-liquidity (ALM) services**

- **Arrakis Pro**: four strategy families (Bootstrap, Flagship, Treasury Diversification, Customized). **[M]** (arrakis.finance blog, accessed 2026-09-10).
- **Gamma Strategies**: non-custodial automated concentrated-liquidity management, active across multiple DEXs since 2021. **[M]** (Consensys blog; Gauntlet "Uniswap ALM Analysis").
- **Revert Finance**: analytics + automation + position management across Uniswap, Sushi, Curve, Balancer; useful primarily as the LP-analytics layer (per-position IL, fee APR, backtesting hooks). **[M]**.
- **Krystal**: CL position manager (found in the same search cluster; not deep-verified here). **[L]**.
- **Aerodrome Slipstream (Base)**: v3-style NFT concentrated positions layered on ve(3,3) gauges (Slipstream launched ~2024-03; unstaked positions keep fees, staked positions route fees through gauges with AERO emissions). SDK/docs exist (`velodrome-finance/docs` sdk.mdx; Wayfinder "Aerodrome Slipstream" SDK; Bitquery gauge-vault API). **[M]**.
- **Hyperliquid**: HLP is a *protocol perp/liquidation market-making vault*, not a spot CLMM; user vaults let an operator run a strategy and share PnL. Relevant as a yield/venue alternative, not as a bid-side launchpad-token LP venue. **[H]** (Hyperliquid protocol-vaults docs).

**Data an app needs to plan and monitor a range**

1. Pool/venue metadata: fee tier, bin step, tick spacing, protocol fee share, pool type (limit-order vs LM). **[H]**.
2. Tick/bin-level liquidity distribution: Uniswap `ticks()`/`liquidityNet` or subgraph tick data; Meteora bin-level API. **[H]**.
3. Volume and volume/TVL history per pool, and (ideally) volume *per price band* to estimate fees crossed inside the target range. **[M]** (pool-level volume is easy; band-level volume requires reconstruction from swap events).
4. Price history since launch: ATH timestamp, drawdown path, time spent in each drawdown bucket, realised volatility, and the launch/migration price (to test "−50% from ATH is still expensive"). **[H]** that the data is obtainable from on-chain swaps; **[M]** for reliable ATH sources on brand-new tokens.
5. Safety/rug signals: mint/freeze authority status, LP burn/lock, holder concentration, deployer history. **[H]** that these matter; sources not evaluated here.
6. Cost model: gas/priority fees, position-account rent, rebalance slippage, and the fee share you actually capture vs other LPs and JIT. **[M]**.
7. Portfolio layer: intra-cohort correlation, common-factor exposure, and a terminal-zero base rate. **[M]**.

---

## Venue feasibility by chain

Status as of **2026-09-10**. "CL bid-side" = can a user place single-sided quote liquidity entirely below spot as a ladder, today, without custom code.

| Chain | Venue(s) | CL bid-side | Launch token pipeline | Status | Confidence |
|---|---|---|---|---|---|
| **Solana** | **Meteora DLMM** (`StrategyType.BidAsk` / selected bins below price; limit-order pool mode) | **Yes, native** | Pump.fun-style launches, Meteora Dynamic Bonding Curve, Raydium migrations | Live, best-fit venue for this proposal (SDK + bin API) | **High** |
| **Ethereum + L2s** | **Uniswap v3 / v4** range orders; v4 limit-order hooks for automation | **Yes** (v3/v4 range order); automation needs a hook or ALM | Direct pool creation for any new token | Live, mature | **High** |
| **Base** | **Aerodrome Slipstream** (v3-style CL + gauges); Uniswap v3/v4 also present | **Yes** (v3-style NFT positions) | Base launchpads/memecoin factories | Live | **Medium–High** |
| **BNB Chain** | PancakeSwap v3 (CL) exists; PancakeSwap v2 (full range) is the default for new four.meme tokens | **Only if the token is in a v3 pool** | four.meme — **switched new memecoin pools from PancakeSwap V3 back to V2 on 2025-03-30** | Practical CL bid-side access to *fresh four.meme* tokens is limited by the V2 default | **Medium** (fact) / **Low–Medium** (feasibility) |
| **HyperEVM** | HyperSwap (first native AMM, 2025-05), KittenSwap (ve(3,3), stable + volatile pools); Hyperliquid HLP is a perp vault, not spot CL | **Not verified** — no concentrated bid-side primitive confirmed | HyperEVM token launches | Live chain; CL LP support unconfirmed in this pass | **Low** |
| **Arc (Circle L1)** | **Synthra** (spot swaps + concentrated liquidity + perps; Arc official Builder Spotlight 2026-07-20; community reports 10M TVL on Arc testnet). ACTFUN launchpad uses a **constant-product AMM** (no CL). TowerExchange = DEX aggregator; RadarDEX = DEX/issuance infrastructure | **Not viable today**: Arc mainnet launches **2026-09-16**; testnet (`chain ID 5042002`, not 5042) has Synthra CL as the only identified candidate | ACTFUN (Mine-to-Launch, graduates to its own CP-AMM) and other launchpads | **Pre-mainnet**; no production CL venue live yet | **Medium–High** on chain status; **Medium** on Synthra; **Low/Unverified** for Tolly, WARP, DYOR, basedpad — no venue capabilities confirmed in this pass |

Practical conclusions:

- The proposal is **technically executable today on exactly two venue families**: Meteora DLMM (best SDK fit, Solana launch tokens) and Uniswap v3/v4 range orders on EVM chains (including via Aerodrome Slipstream for Base tokens). Everything else in the table is either a full-range V2-style pool, a perp vault, or pre-mainnet.
- On **Arc**, do not design around it yet: mainnet is 6 days away at the time of writing, the only concentrated-liquidity venue identified is Synthra on testnet, and the launchpad (ACTFUN) graduates tokens into a constant-product AMM with no bid-side primitive. Re-check after mainnet and after ACTFUN/TowerExchange/RadarDEX publish LP mechanics.
- On **BNB/four.meme**, the March 2025 reversion of new memecoin pools to PancakeSwap V2 means the default graduate pool has no concentrated bid-side primitive; a bid-side strategy there would require the token to be in a v3 pool (or creating one).

---

## Sources

Format: URL — date — one-line claim. Dates are publication dates where known, otherwise the access date (all accesses 2026-09-10).

1. https://developers.uniswap.org/docs/get-started/concepts/liquidity-providers/range-orders — undated, accessed 2026-09-10 — Range orders = single-sided liquidity to approximate limit orders; below-spot price space is denominated in the quote asset, so buy-limit range orders are funded with quote; range orders can go unfilled if price reverses; buy-stop and stop-loss orders are impossible; maker earns fees while filled.
2. https://blog.uniswap.org/uniswap-v3-math-primer-2 — 2023-06-26 — Authoritative holdings formulas (in-range/out-of-range), `token0 = ℓ(√p_u−√p')/(√p'√p_u)`, `token1 = ℓ(√p'−√p_l)`, liquidity from real reserves, and uncollected-fee accounting via fee-growth accumulators; "The liquidity math in Uniswap v4 is the same as v3".
3. https://developers.uniswap.org/docs/get-started/concepts/fees — undated, accessed 2026-09-10 — Standard v3 fee tiers 0.05% / 0.30% / 1.00%.
4. https://docs.meteora.ag/core-products/dlmm/formulas — undated, accessed 2026-09-10 — Bin price `P_i=(1+bin_step/10,000)^i`; bin invariant `L=P·x+y`; swap rounding rules; `total fee = min(base+variable, 10%)`; `base fee = base_factor × bin_step × 10 × 10^power`; variable-fee formula from the volatility accumulator; protocol share ≤ 25% (2,500 bps).
5. https://docs.meteora.ag/core-products/dlmm/what-is-dlmm — undated, accessed 2026-09-10 — Bins and the active bin; bin step up to 400 bps; bin arrays of 70 with `PositionV2` up to 1,400 bins; Spot/Curve/Bid-Ask shapes; pool function modes for liquidity mining vs limit-order liquidity; limit-order liquidity uses bid-side/ask-side bins.
6. https://docs.meteora.ag/core-products/dlmm/strategies-and-use-cases — undated, accessed 2026-09-10 — Bid-Ask = inverse Curve with more liquidity at the edges; DCA-in = single-sided quote below current price; "DLMM strategies ... do not remove impermanent loss or out-of-range risk"; Bid-Ask "may sit away from the active price until the market moves into the edge bins".
7. https://docs.meteora.ag/core-products/dlmm/collect-fee-mode — undated, accessed 2026-09-10 (search snippet) — Pool-level setting that determines which token trading fees are collected in during swaps.
8. https://www.npmjs.com/package/@meteora-ag/dlmm — v1.9.10, published ~2026-08 — SDK surface: `DLMM.create`, `getActiveBin`, `initializePositionAndAddLiquidityByStrategy`, `StrategyType.Spot|BidAsk|Curve`, `autoFillYByStrategy`, pool list at `dlmm-api.meteora.ag/pair/all`.
9. https://github.com/MeteoraAg/dlmm-sdk and https://github.com/meteora-invent/studio — accessed 2026-09-10 — Limit-order pool config references `concreteFunctionType: 0` and deposits into up to 50 bins (indicative of the limit-order mode).
10. https://arxiv.org/abs/2404.05803 — Fritsch & Canidio, v1 2024-04-08 / v2 2024-04-22 — Arbitrage losses (LVR) exceed fees in many large Uniswap pools; v2 more profitable than v3 for passive LPs; faster blocks cut LVR by 20–70%.
11. https://arxiv.org/abs/2208.06046 — Milionis, Moallemi, Roughgarden, Zhang; v1 2022-08-11, v5 2024-05-27 — Defines loss-versus-rebalancing as the main adverse-selection cost of AMM LPs; model matches empirical LP returns.
12. https://arxiv.org/abs/2205.09153 (Heimbach et al., "Risks and Returns of Uniswap V3 Liquidity Providers") — 2022-05-18 — Theoretical model; abstract notes small returns and little loss risk for the studied normal pairs, and cites an earlier ~50%-of-positions-lose-money empirical result.
13. https://www.reddit.com/r/solana/comments/1jq5rdl/automated_memecoin_farming_via_meteora_dlmm_24/ — posted ~2025-03 (Reddit "1y ago" at access) — Operator reports bot-run one-sided SOL-only DLMM positions with wide downside ranges, ~2 SOL per position, "works out most of the time" because memecoins are volatile; PnL posted only as screenshots.
14. https://bytwork.com/en/defi/meteora — updated 2026-08-08 — Tutorial recommending Bid-Ask single-sided memecoin entries around −50% to −90% and claiming "losses at the lower boundary are only about 22%"; the figure is inconsistent with the stated range (see Evidence section).
15. https://solidity-by-example.org/defi/uniswap-v4-limit-order/ — accessed 2026-09-10 — V4 limit-order hook pattern: `placeLimitOrder(tick, direction)`, hook custody, `afterSwap` fill detection, `getHookPermissions`.
16. https://www.openzeppelin.com/news/six-questions-to-ask-before-writing-a-uniswap-v4-hook — 2025-06-10 — Hooks that call `modifyLiquidity` own the liquidity and must handle its accounting/security.
17. https://docs.mav.xyz (Liquidity Strategies) — 2024-07-22 — Maverick exposes Mode Static plus movement modes; "Mode Right" tracks the base asset's price downward, keeping the bottom of the range at the current price (native bid-side accumulation mode).
18. https://coinmarketcap.com/currencies/maverick-protocol/ — accessed 2026-09-10 — Corroborates the Mode Right description ("keeping the bottom of the price range at the current price").
19. https://arrakis.finance/blog/guide-arrakis-pro-liquidity-management-strategies-token-issuers — accessed 2026-09-10 — Arrakis Pro's four liquidity strategies: Bootstrap, Flagship, Treasury Diversification, Customized.
20. https://consensys.io/blog/gamma-strategies-an-innovative-solution-to-the-challenge-of-liquidity-management — accessed 2026-09-10 — Gamma provides non-custodial automated concentrated-liquidity management.
21. https://revert.finance/ — accessed 2026-09-10 — LP analytics, automation and position management for Uniswap, Sushiswap, Curve, Balancer.
22. https://github.com/velodrome-finance/docs (sdk.mdx) and https://aerodrome.finance (docs) — accessed 2026-09-10 — Aerodrome includes a constant-product AMM plus Slipstream concentrated liquidity; concentrated positions are NFT-based, with gauge staking and fee routing.
23. https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/vaults/protocol-vaults — 2026-08-17 — HLP is a protocol vault providing liquidity via multiple market-making strategies (perps), distinct from a spot CLMM.
24. https://hype.global/... (KittenSwap) — 2026-06-17 — KittenSwap is a community-owned ve(3,3) DEX on HyperEVM with stable and volatile pools. https://cryptonews.net (HyperSwap) — 2025-05-09 — HyperSwap is the first native AMM DEX on HyperEVM.
25. https://www.chaincatcher.com / https://www.odaily.news — 2025-03-31 / 2025-04-01 — four.meme adjusted its liquidity pools: new memecoin pools moved to PancakeSwap V2, abandoning V3, after a period of V3 usage. (https://www.binance.com news item, 2025-03-29, corroborates the announcement date.)
26. https://www.circle.com/pressroom/circle-announces-founding-validator-cohort-and-major-integrations-for-arc-ahead-of-september-16-mainnet-launch — accessed 2026-09-10 — Arc mainnet launch scheduled for 2026-09-16.
27. https://actfudoc.mintlify.app — accessed 2026-09-10 — ACTFUN on Arc Testnet (**Chain ID 5042002**): Pump.fun-style launchpad; tokens graduate into a **constant-product AMM** built into the same contract; no concentrated liquidity.
28. https://community.arc.io/public/videos/builder-spotlight-synthra-spot-concentrated-liquidity-and-perpetual-markets-on-arc-2026-07-20 — 2026-07-20 — Arc official Builder Spotlight: Synthra brings spot swaps, concentrated liquidity and perpetual markets on Arc Testnet. https://x.com/synthra_swap/status/1993662573950976149 — Synthra reports 10M TVL on Arc Testnet.
29. https://www.binance.com / https://www.weex.com / https://www.rootdata.com Arc ecosystem overviews — 2026-07-23 and later — Arc ecosystem project roundups naming TowerExchange (DEX aggregator), RadarDEX (DEX/issuance), ACTFUN (launchpad); Tolly, WARP, DYOR and basedpad were not confirmed with documented LP mechanics in this pass.
30. https://www.gauntlet.xyz/resources/uniswap-alm-analysis — accessed 2026-09-10 — Comparative analysis of Uniswap ALMs (Arrakis low-risk focus; Gamma across many DEXs).

**Explicit non-findings (for honesty):** no public, quantitative backtest of a bid-side CLMM ladder on launchpad/memecoin tokens was located; no measurement of intra-cohort correlation across ~15 simultaneous launchpad LP positions was located; no primary-data base rate for "launchpad token reaches −50% then recovers" was located. These three gaps are the highest-value items to close before sizing this strategy.
