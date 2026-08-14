# ag-09 Funding Analysis Report

## Executive Summary

This analysis examines whether funding rates (perpetual swap sentiment indicators) predict future returns across 9 major crypto perps on Hyperliquid. The study tests four hypotheses: crowding-reversal, weekday interactions, crash antecedents, and funding mean-reversion. Results are mixed: funding shows strong persistence but limited predictive power for price direction, with some evidence of mean-reversion in extreme positions.

---

## Question 1: Does Crowding Predict Reversal?

### Hypothesis
Extreme positive funding (crowd long) should predict negative forward returns; extreme negative funding should predict positive forward returns.

### Methodology
- Computed per-coin funding z-scores using each coin's historical funding distribution
- Buckets: extreme negative (< -1.5σ), normal (±1.5σ), extreme positive (> +1.5σ)
- Analyzed next-1-day and next-5-day returns
- Split-sample validation (50/50 by time per coin)

### Findings

**Sample sizes:** 
- Extreme negative: 262 observations
- Normal: 7,450 observations  
- Extreme positive: 263 observations

**Next 1-Day Returns:**
- Extreme negative: **+0.25%** (first half), +1.09% (second half)
- Normal: +0.19% (first half), +0.14% (second half)
- Extreme positive: **+0.46%** (first half), insufficient data in second half

**Next 5-Day Returns:**
- Extreme negative: -0.14% (first half), -1.46% (second half)
- Normal: +0.69% (first half), +0.44% (second half)
- Extreme positive: **-1.15%** (first half), insufficient data in second half

### Verdict: **NO REVERSAL EFFECT FOUND**

Contrary to the crowding-reversal hypothesis, extreme positive funding showed **positive** next-day returns (+0.46%) rather than negative. The 5-day horizon showed slight negative returns for extreme positive funding (-1.15%), but this effect did not replicate in the second half due to insufficient sample size.

**Per-coin replication:** The pattern was inconsistent across coins, with some showing reversal and others showing continuation.

**Honest assessment:** Funding extremes do not reliably predict price reversals at the 1-day or 5-day horizon in this dataset.

---

## Question 2: Does Funding Explain the Weekday Pattern?

### Context from ag-05/ag-06
Previous analysis found Monday and Wednesday show weaker returns. This study examines whether funding rates differ by weekday and whether controlling for funding changes the weekday pattern.

### Methodology
- Computed average funding rate by weekday (UTC)
- Computed average next-day return by weekday
- Examined correlation between funding levels and returns

### Findings

**Average Funding by Weekday (nearly uniform):**
- Monday: 0.000023 (23 bps)
- Tuesday: 0.000024 (24 bps)
- Wednesday: 0.000023 (23 bps)
- Thursday: 0.000023 (23 bps)
- Friday: 0.000024 (24 bps)
- Saturday: 0.000025 (25 bps)
- Sunday: 0.000025 (25 bps)

**Average Next-Day Returns by Weekday:**
- Monday: +0.10%
- Tuesday: +0.52%
- Wednesday: **-0.63%** (weakest)
- Thursday: +0.38%
- Friday: +0.37%
- Saturday: +0.07%
- Sunday: +0.39%

### Verdict: **FUNDING DOES NOT EXPLAIN WEEKDAY PATTERN**

Funding rates are essentially flat across weekdays (variation < 2 bps), while returns vary meaningfully (Monday/Wednesday weakness). Since funding doesn't vary by day, it cannot explain the weekday return pattern.

**Honest assessment:** The weekday pattern appears to be independent of funding sentiment. It may be driven by liquidity, institutional flows, or other factors not captured by funding rates.

---

## Question 3: Does Extreme Funding Before Crashes Predict Different Reversion?

### Methodology
- Defined daily crashes as next-1-day return ≤ -5%
- Categorized crashes by pre-crash funding bucket
- Analyzed next-5-day returns after crashes

### Findings

**Crash distribution (700 total crashes):**
- Normal funding pre-crash: 653 crashes (93.3%)
- Extreme negative funding pre-crash: 17 crashes (2.4%)
- Extreme positive funding pre-crash: 30 crashes (4.3%)

**Next 5-Day Returns After Crashes:**
- Normal funding: **-0.19%** (continuation)
- Extreme negative: -1.07% (worse reversion)
- Extreme positive: **+4.18%** (strong reversion)

### Verdict: **MIXED EVIDENCE, SMALL SAMPLES**

Crashes preceded by extreme positive funding showed strong positive 5-day returns (+4.18%), suggesting reversion. However, the sample is tiny (30 crashes vs 653 normal). Extreme negative funding pre-crash showed worse reversion (-1.07%), contrary to expectations.

**Sample size warning:** Extreme funding buckets have insufficient observations for reliable inference (<100 obs per bucket per timeframe, per methodology rules).

**Honest assessment:** There's a hint that extreme positive funding before crashes may predict stronger reversion, but the sample is too small to draw firm conclusions. More data needed.

---

## Question 4: Does Funding Mean-Revert?

### Methodology
- Computed funding autocorrelation at 1-day, 7-day, and 30-day lags
- Analyzed duration of extreme funding spells (>1.5σ)

### Findings

**Funding Autocorrelation by Coin:**

| Coin | 1-Day | 7-Day | 30-Day |
|------|-------|-------|--------|
| SOL  | 0.80  | 0.68  | 0.66   |
| AAVE | 0.72  | 0.53  | 0.34   |
| CRV  | 0.64  | 0.58  | 0.32   |
| XRP  | 0.60  | 0.46  | 0.20   |
| ETH  | 0.56  | 0.10  | 0.09   |
| BTC  | 0.53  | 0.24  | 0.09   |
| ZEC  | 0.34  | 0.07  | -0.12  |
| PUMP | 0.06  | 0.34  | 0.00   |
| LIT  | 0.00  | 0.00  | 0.00   |

**Extreme Funding Spell Durations:**
- **Negative extremes:** 105 spells, avg 2.3 days, median 1 day, max 29 days
- **Positive extremes:** 145 spells, avg 1.8 days, median 1 day, max 11 days

### Verdict: **FUNDING IS HIGHLY PERSISTENT, SLOW TO MEAN-REVERT**

Funding rates show strong short-term persistence (0.5-0.8 autocorrelation at 1-day lag). Mean-reversion is slow: only some coins (ETH, BTC, ZEC) show near-zero autocorrelation at 30 days, while others (SOL, AAVE) remain persistent.

**Half-life estimate:** Based on autocorrelation decay, extreme funding spells typically last 1-2 days, but can persist for weeks (max 29 days for negative extremes).

**Honest assessment:** Funding is not a fast mean-reverting signal. Extreme positioning can persist for extended periods, making it a regime indicator rather than a timing tool.

---

## Cross-Coin Replication Analysis

### Per-Coin Consistency
Funding bucket returns varied widely across coins:
- Some coins showed reversal (e.g., BTC extreme positive → negative 5-day returns)
- Others showed continuation (e.g., SOL extreme positive → positive 5-day returns)
- No consistent pattern across all 9 coins

**Replication rate:** < 50% of coins showed the same directional effect for extreme funding buckets.

### Verdict: **NO CONSISTENT CROSS-COIN EFFECT**

The funding-reversal hypothesis does not replicate consistently across coins. This suggests that any observed effects may be coin-specific or driven by a few outliers rather than a universal market mechanism.

---

## Null Results Summary

This analysis found **no robust evidence** that:
1. Extreme funding predicts price reversals (contrary to hypothesis)
2. Funding explains the weekday return pattern (funding is flat across days)
3. Extreme funding before crashes reliably predicts reversion (sample too small)
4. Funding mean-reverts quickly enough to be a timing signal (highly persistent)

**Honest conclusion:** Funding rates on Hyperliquid appear to be a persistent sentiment indicator but do not provide a reliable edge for predicting short-term price movements. The documented perp funding-reversal phenomenon from other markets/periods does not manifest clearly in this dataset.

---

## Methodology Notes

- **Data:** 118,545 funding rows, 7,975 daily candles with funding across 9 coins
- **Convention:** Funding at day's open (most recent hourly funding ≤ candle open)
- **Z-scores:** Computed per-coin to account for different funding levels
- **Buckets:** Extreme = |z| > 1.5, Normal = |z| ≤ 1.5
- **Split-sample:** 50/50 by time per coin for validation
- **Pitfalls addressed:** XMR excluded (0 funding rows), fundingRate cast to float, per-coin z-scores

---

## Limitations

1. **Sample size:** Extreme funding buckets have limited observations (<300), reducing statistical power
2. **Time period:** Data spans ~May 2023 to present; may not represent all market regimes
3. **Coin coverage:** Only 9 coins with funding data; excludes DOGE, HYPE, XMR
4. **Funding frequency:** Hourly funding vs daily candles may miss intraday extremes
5. **Market regime:** Results may be specific to the current market structure on Hyperliquid

---

## Recommendations for Future Research

1. **Increase sample size:** Include more coins and longer time history
2. **Intraday analysis:** Use hourly candles with hourly funding for finer-grained analysis
3. **Regime analysis:** Test whether funding effects differ by volatility/liquidity regimes
4. **Cross-exchange comparison:** Compare Hyperliquid funding effects to other perp markets
5. **Nonlinear effects:** Test thresholds beyond ±1.5σ (e.g., ±2σ, ±3σ)

---

**Report generated:** 2026-08-14  
**Analysis window:** ag-09-funding  
**Data period:** ~May 2023 – August 2026