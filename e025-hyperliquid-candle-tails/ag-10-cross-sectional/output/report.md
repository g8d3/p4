# ag-10 — Cross-Sectional: Relative Strength & Co-Movement

**Data**: 12 coins, 1d candles, 2023-01-01 to 2026-08-13. Cross-sectional
work uses 1d timeframe (12 coins x ~1300 days each, except HYPE 617, PUMP
400, LIT 235).

**Caveat**: 12 coins is a small cross-section. A 3-coin portfolio (top/bottom
bucket) has high idiosyncratic risk. Results are suggestive, not definitive.

---

## Q1: Does Relative Strength Persist (Momentum)?

**Method**: Each day, rank the 12 coins by trailing N-day return (N=5, 20).
Bucket into top 3 / middle 6 / bottom 3. Measure next-day and next-5-day
return of each bucket.

### Trail 5-day ranking

| Bucket | Next-day mean | Next-day median | Next-5d mean | Next-5d median | n |
|--------|--------------|-----------------|-------------|----------------|-----|
| Top 3 | +0.29% | -0.09% | +1.59% | +0.08% | 3945 |
| Middle | +0.16% | +0.00% | +0.45% | -0.09% | 5107 |
| Bottom 3 | +0.06% | +0.05% | +0.56% | +0.16% | 3960 |

### Trail 20-day ranking

| Bucket | Next-day mean | Next-day median | Next-5d mean | Next-5d median | n |
|--------|--------------|-----------------|-------------|----------------|-----|
| Top 3 | +0.35% | +0.00% | +1.62% | +0.25% | 3900 |
| Middle | +0.03% | -0.04% | +0.22% | -0.12% | 5152 |
| Bottom 3 | +0.17% | +0.05% | +0.83% | +0.07% | 3960 |

### Split-sample (OOS: second half only)

**N=5, H2**: Top3 next-day +0.36%, Bottom3 +0.13%. Gap = +0.23pp.
**N=20, H2**: Top3 next-day +0.58%, Bottom3 +0.17%. Gap = +0.41pp.
**N=20, H2**: Top3 next-5d +2.58%, Bottom3 +0.81%. Gap = +1.77pp.

### Verdict

**Mild momentum confirmed.** Top 3 coins by trailing return beat bottom 3 on
both next-day and next-5-day horizons. The effect is stronger on the 20-day
lookback (N=20) and on the 5-day forward horizon. Split-sample replication
holds: the edge is present and even larger in the second half. However, the
medians are near zero or negative for all buckets — the means are pulled up by
large positive outliers. This is a fat-tail momentum effect: winners keep
winning in big moves, not consistently every day.

---

## Q2: Does the Long-Short Portfolio Make Money?

**Method**: Each day in the OOS period (second half of data), go long the
top-3 coins by trailing N-day return and short the bottom-3, equal weight,
hold one day. Report net of taker fees (0.045% per side, 0.09% round trip
for the 2-leg position).

### N=5 Long-Short (OOS)

| Metric | Value |
|--------|-------|
| Trading days | 659 |
| Total return | +103.8% |
| Mean daily | +0.169% |
| Sharpe | 0.76 |
| Max drawdown | -52.8% |
| Win rate | 50.2% |

### N=20 Long-Short (OOS)

| Metric | Value |
|--------|-------|
| Trading days | 659 |
| Total return | +341.3% |
| Mean daily | +0.288% |
| Sharpe | 1.28 |
| Max drawdown | -66.3% |
| Win rate | 51.3% |

### Verdict

**Yes, but with huge risk.** The N=20 long-short portfolio returned +341%
over ~2.5 years OOS, net of fees, with a Sharpe of 1.28. This is a real edge
that survives transaction costs. However, the max drawdown of -66% makes it
unusable without position sizing or risk management. The win rate is barely
above 50% — the edge comes from the magnitude of wins vs losses (fat tails),
not from high hit rate.

**Key caveat**: 12 coins is a tiny cross-section. A 3-coin long portfolio has
massive idiosyncratic risk. In a real market with 50+ assets, the
diversification would improve the Sharpe and reduce drawdowns.

**The fee impact**: at 0.09% round trip, fees eat ~0.09% of the ~0.29%
mean daily gross, consuming about 31% of the edge. This is manageable but
significant.

---

## Q3: Do Crashes Hit Everything at Once?

**Method**: For each coin, find days where its 1d return exceeds +/-3 standard
deviations (per-coin z-score). On those event days, check what fraction of
the other 11 coins moved in the same direction.

### Results

| Event direction | # events | Mean % coins same dir | Median | Expected if independent |
|----------------|----------|----------------------|--------|------------------------|
| **Down** (crash) | 57 | **96.3%** | 100% | 50% |
| **Up** (squeeze) | 130 | **84.2%** | 100% | 50% |

### Per-coin breakdown (selected)

| Trigger coin | Direction | # events | Mean co-movement |
|-------------|-----------|----------|-----------------|
| BTC | Down | 7 | 98.6% |
| BTC | Up | 16 | 94.0% |
| ETH | Down | 8 | 97.6% |
| ETH | Up | 15 | 95.4% |
| SOL | Down | 4 | 97.5% |
| SOL | Up | 9 | 77.6% |
| XMR | Down | 8 | 88.7% |
| XMR | Up | 11 | 73.7% |

### Verdict

**Yes — there is a massive market factor in the tails.** When any coin
crashes (3σ down), 96% of the other coins also drop that day. This is far
above the 50% expected under independence. Upside squeezes show 84%
co-movement — strong but weaker than crashes.

**Implication for diversification**: In normal times, these 12 coins may
diversify somewhat. In tails, diversification evaporates. A "diversified"
crypto portfolio loses everything at once during crashes. This is the
systematic risk that makes crypto tail risk so dangerous.

**BTC and ETH lead**: their 3σ events show the highest co-movement (94-95%),
confirming they drive the market. XMR and SOL show lower co-movement on up
moves (74-78%), suggesting more idiosyncratic upside.

---

## Summary of Findings

| Question | Answer | Confidence |
|----------|--------|------------|
| Q1: Momentum persists? | **Yes, mild** — top 3 beat bottom 3 by 0.2-0.4pp/day | Medium (split-sample holds, but means driven by outliers) |
| Q2: Long-short makes money? | **Yes** — +341% OOS net of fees (N=20), Sharpe 1.28 | Medium (real edge, but -66% DD, tiny cross-section) |
| Q3: Crashes hit everything? | **Yes, strongly** — 96% co-movement on down 3σ days | High (unambiguous result) |

### What this means for the broader experiment

1. **Cross-sectional momentum is real in crypto** — winners keep winning over
   weeks, consistent with the academic literature on crypto momentum.
2. **Tail risk is systematic** — diversification across coins does not protect
   against crashes. This is critical for position sizing (ag-11 vol model).
3. **The edge survives fees** — taker costs of 0.09% round trip consume ~31%
   of the gross edge, but the net is still positive and meaningful.
4. **Small cross-section caveat**: 12 coins with a 3-coin bucket means high
   idiosyncratic risk. Results would likely improve (lower variance, better
   Sharpe) with 50+ coins.
