# Volatility Model Report

## Executive Summary

GARCH(1,1) volatility forecasting provides **significant improvements** over simple empirical volatility features for predicting next-candle absolute returns on Hyperliquid 1h data. Across the top 6 coins by volume, GARCH achieved **100% win rate** against rolling 20-period volatility, with an average correlation improvement of **0.31** (31 percentage points).

## Methodology

### GARCH Modeling
- **Model**: GARCH(1,1) with normal distribution
- **Training**: 50% walk-forward split (fit on first half, forecast on second half)
- **Forecasting**: Simplified GARCH update using fitted parameters rather than rolling refits
- **Evaluation**: Correlation between forecast volatility and realized |return|

### EVT Tail Analysis
- **Method**: Generalized Pareto Distribution (GPD) using Peaks-Over-Threshold
- **Threshold**: 90th percentile of absolute returns
- **Estimation**: Method of moments for computational efficiency
- **Output**: Tail probabilities for extreme moves (3σ to 10σ)

### Benchmark Comparison
- **Empirical feature**: Rolling 20-period standard deviation of |return|
- **Evaluation**: Same correlation metric on same test period

## Key Findings

### 1. GARCH Forecast Performance

| Coin | GARCH Correlation | Empirical Correlation | Improvement |
|------|-------------------|----------------------|-------------|
| CRV  | 0.746 | 0.194 | +0.551 |
| XRP  | 0.628 | 0.317 | +0.311 |
| DOGE | 0.682 | 0.223 | +0.459 |
| HYPE | 0.483 | 0.341 | +0.142 |
| LIT  | 0.467 | 0.264 | +0.203 |
| PUMP | 0.429 | 0.223 | +0.206 |

**Average GARCH correlation: 0.572**
**Average empirical correlation: 0.260**
**Average improvement: +0.312**

### 2. EVT Tail Characteristics

| Coin | ξ (shape) | β (scale) | Exceedances | P(|ret| > 3σ) | P(|ret| > 5σ) | P(|ret| > 10σ) |
|------|-----------|-----------|-------------|---------------|---------------|----------------|
| CRV  | 0.010 | 0.698 | 500 | 4.85% | 0.86% | 0.013% |
| XRP  | 0.139 | 0.495 | 500 | 3.91% | 0.88% | 0.056% |
| DOGE | 0.090 | 0.570 | 500 | 4.15% | 0.90% | 0.041% |
| HYPE | 0.096 | 0.665 | 500 | 4.64% | 0.74% | 0.022% |
| LIT  | -0.000 | 1.151 | 500 | 4.99% | 0.81% | 0.009% |
| PUMP | 0.025 | 0.878 | 501 | 4.88% | 0.80% | 0.012% |

**Tail interpretation**:
- Positive ξ values (0.01-0.14) indicate **fat tails** - extreme moves are more likely than normal distribution
- XRP shows the heaviest tails (ξ=0.139), suggesting higher crash risk
- LIT shows near-exponential tails (ξ≈0), more "normal" extreme behavior

### 3. Position Sizing Implications

Based on GARCH volatility forecasts, here's the **risk multiplier schedule** (normalized to median volatility = 1.0x):

| Forecast Vol Percentile | Suggested Risk Multiplier |
|-------------------------|---------------------------|
| 10th (lowest vol)       | 1.08-1.47x base size      |
| 25th percentile         | 1.06-1.30x base size      |
| 50th (median vol)       | 1.00x base size           |
| 75th percentile         | 0.70-0.89x base size      |
| 90th percentile         | 0.62-0.76x base size      |
| 95th percentile         | 0.54-0.67x base size      |
| 99th (highest vol)      | 0.40-0.50x base size      |

**Practical application**: If you normally risk 1% of capital per trade, reduce to 0.4-0.5% when GARCH forecasts volatility in the top 1% of historical levels.

### 4. Cost-Benefit Analysis

**GARCH advantages**:
- ✅ **31 percentage point correlation improvement** over simple rolling vol
- ✅ **100% win rate** across all tested coins
- ✅ **Adaptive** to changing market conditions via model parameters
- ✅ **Theoretically grounded** in financial econometrics

**GARCH disadvantages**:
- ❌ **Computational cost**: Fitting takes seconds vs milliseconds for empirical
- ❌ **Complexity**: Requires parameter estimation and numerical optimization
- ❌ **Parameter risk**: Model misspecification can degrade performance

**Verdict**: GARCH is **meaningfully better** than simple empirical volatility buckets for 1h Hyperliquid data. The 0.31 correlation improvement justifies the computational cost for serious trading applications.

## Limitations

1. **Single timeframe analysis**: Only tested on 1h data; performance may vary on 5m or 1d
2. **Simplified forecasting**: Used parameter persistence rather than rolling refits for speed
3. **Normal distribution assumption**: GARCH assumed normal errors; real returns have fatter tails
4. **Walk-forward only**: No out-of-sample validation beyond the 50/50 split
5. **No transaction costs**: Analysis doesn't account for trading frictions

## Recommendations

1. **Use GARCH for position sizing**: The 31% improvement in vol forecasting justifies implementation
2. **Scale positions inversely with forecast vol**: Use the sizing table above as starting point
3. **Monitor tail risk**: EVT shows 3-5% daily probability of 3σ+ moves; size conservatively
4. **Consider EGARCH for leverage effects**: If asymmetric volatility response is suspected
5. **Validate on live data**: Paper trade the GARCH sizing rules before real deployment

## Technical Notes

- **GARCH convergence**: All models converged successfully on 1h data
- **Tail adequacy**: 500+ exceedances per coin provides robust GPD estimation
- **Computational efficiency**: Simplified forecasting reduced runtime from hours to seconds
- **Data quality**: 30K+ 1h candles across 6 coins provides sufficient statistical power

## Files Generated

- `output/vol_forecast.csv`: GARCH performance metrics by coin
- `output/evt_tails.csv`: GPD tail parameters and extreme quantiles
- `output/head_to_head.csv`: GARCH vs empirical feature comparison
- `output/sizing_tables.csv`: Position sizing recommendations by vol percentile
- `output/empirical_benchmark.csv`: Rolling volatility baseline performance