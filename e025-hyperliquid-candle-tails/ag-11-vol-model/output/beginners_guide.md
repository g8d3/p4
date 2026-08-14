# Beginner's Guide to GARCH and EVT for Position Sizing

## Why Volatility Matters for Position Sizing

**Position sizing is how much money you risk on each trade.** If you risk the same dollar amount regardless of market conditions, you'll get crushed during volatile periods and miss opportunities during calm periods.

**Volatility clustering** is a real phenomenon: quiet periods tend to follow quiet periods, and wild periods tend to follow wild periods. GARCH helps us predict whether tomorrow will be calm or wild.

## GARCH in Plain English

**GARCH** (Generalized Autoregressive Conditional Heteroskedasticity) is a fancy name for a simple idea: **today's volatility depends on yesterday's volatility and yesterday's surprise move**.

### The GARCH(1,1) Formula

```
Tomorrow's volatility² = ω + α × (today's surprise)² + β × (today's volatility)²
```

Where:
- **ω (omega)**: Long-term average volatility (the baseline)
- **α (alpha)**: How much today's surprise moves tomorrow's volatility (reaction speed)
- **β (beta)**: How much today's volatility persists (memory)

### What This Means in Practice

- If **α is high**: The market overreacts to surprises (volatility spikes quickly)
- If **β is high**: Volatility is persistent (once volatile, stays volatile)
- **α + β < 1**: Volatility eventually returns to normal (stationary)
- **α + β close to 1**: Volatility clusters persist for a long time

### Real-World Example

Suppose Bitcoin just had a 5% move (big surprise). A GARCH model might say:

1. **Normal day**: Volatility = 2%
2. **After 5% move**: Volatility jumps to 4% tomorrow
3. **Day after**: Volatility = 3.5% (still elevated but fading)
4. **Week later**: Volatility back to 2% (normal)

This clustering effect is exactly what GARCH captures.

## EVT (Extreme Value Theory) in Plain English

**EVT** helps us answer: "What's the chance of a catastrophic move that I've never seen before?"

### The Problem with Normal Distributions

Finance assumes normal (bell curve) distributions, but real markets have **fat tails**:
- Normal distribution: 3σ event = 0.1% chance (once per 3 years)
- Real crypto markets: 3σ event = 4% chance (once per month!)

### GPD (Generalized Pareto Distribution)

EVT uses the **Generalized Pareto Distribution** to model the **tail** - the extreme moves beyond a threshold.

**Key parameter: ξ (xi)** - the shape parameter
- **ξ = 0**: Exponential tails (like normal distribution)
- **ξ > 0**: Fat tails (extreme moves more likely than normal)
- **ξ < 0**: Thin tails (extreme moves less likely than normal)

### What This Means for Trading

If **ξ = 0.1** (typical for crypto):
- A 5σ move is **100x more likely** than under normal distribution
- You'll see crashes that "should never happen" several times per year
- Position sizing must account for this fat-tail risk

## How to Use This for Position Sizing

### Step 1: Forecast Tomorrow's Volatility

Use GARCH to predict σ (sigma) for the next candle:
- If forecast σ = 2% → normal volatility
- If forecast σ = 4% → high volatility (reduce position size)
- If forecast σ = 1% → low volatility (can increase position size)

### Step 2: Scale Position Size Inversely to Volatility

**Basic fixed-fractional rule**:
```
Position size = (Base risk %) ÷ (Forecast volatility %)
```

Example:
- Base risk = 1% of capital per trade
- Normal day (σ = 2%): Risk 1% ÷ 2% = 0.5x base position
- Volatile day (σ = 4%): Risk 1% ÷ 4% = 0.25x base position
- Calm day (σ = 1%): Risk 1% ÷ 1% = 1.0x base position

### Step 3: Check Tail Risk with EVT

Before entering a trade, ask: "What's the chance of a 5σ move against me?"

From our EVT analysis:
- Typical crypto: P(|ret| > 5σ) ≈ 0.8% (about once per 4 months)
- This means **catastrophic moves are rare but real**

**Practical rule**: If EVT says P(5σ move) > 1%, reduce position by another 25%.

## Concrete Example: Trading Bitcoin

### Scenario 1: Normal Volatility Day
- GARCH forecast: σ = 2.5%
- Your base risk: 1% of $10,000 = $100
- Position size: $100 ÷ 2.5% = $4,000 position
- EVT check: P(5σ) = 0.8% ✓ acceptable
- **Final trade**: $4,000 long position

### Scenario 2: High Volatility Day
- GARCH forecast: σ = 5.0%
- Your base risk: 1% of $10,000 = $100  
- Position size: $100 ÷ 5% = $2,000 position
- EVT check: P(5σ) = 1.2% ⚠️ elevated
- Additional reduction: $2,000 × 0.75 = $1,500
- **Final trade**: $1,500 long position (conservative)

## Why This Beats Simple Rules

### Old Way: Fixed Dollar Risk
- Always risk $500 per trade
- Problem: $500 is 5% of account during calm periods, 0.5% during volatility

### Better Way: Rolling Volatility
- Risk 1% ÷ 20-day rolling σ
- Problem: Reacts slowly, doesn't capture clustering

### Best Way: GARCH + EVT
- GARCH predicts tomorrow's volatility (forward-looking)
- EVT quantifies tail risk (catastrophic moves)
- Result: Proactive, adaptive position sizing

## Common Mistakes to Avoid

### ❌ Mistake 1: Ignoring Volatility Clustering
Trading the same size during FTX collapse as during normal markets.

### ❌ Mistake 2: Assuming Normal Distribution
Thinking 3σ moves "never happen" when they happen monthly in crypto.

### ❌ Mistake 3: Overfitting GARCH
Using GARCH(5,5) when GARCH(1,1) works better and is more stable.

### ❌ Mistake 4: Ignoring Model Risk
Blindly following GARCH signals without checking for regime changes.

## How to Implement This

1. **Start simple**: Use GARCH(1,1) with normal distribution
2. **Validate**: Check if forecast σ correlates with realized |ret|
3. **Scale gradually**: Don't jump to 0.25x positions overnight
4. **Monitor**: Track if GARCH improves your risk-adjusted returns
5. **Iterate**: Try EGARCH if you suspect asymmetric volatility effects

## Key Takeaways

1. **Volatility clusters**: Quiet follows quiet, wild follows wild
2. **GARCH predicts this**: Better than simple rolling averages
3. **Tails are fat**: Crypto has more extreme moves than normal distribution
4. **Size inversely to vol**: High vol → smaller positions, low vol → larger positions
5. **Start simple**: GARCH(1,1) + basic sizing rules beat no model at all

**Remember**: The goal isn't perfect predictions - it's consistently better risk management than guessing.