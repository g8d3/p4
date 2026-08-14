# Beginner's guide: fees, slippage, breakeven — and why costs kill edges

This is the "why" behind the entire experiment's final verdict. Read this
before the report if you're new to trading costs.

## 1. Trading is not free

Every time you trade on an exchange, you pay. Two kinds of costs matter:

**Fees** — the exchange's cut. On Hyperliquid:
- **Taker** order (you cross the book, i.e. market order): **0.045% per side**.
  Buy + sell = **0.09% round trip**. This is the worst case and what we use.
- **Maker** order (you rest a limit order someone else hits): **0.018% per
  side** = 0.036% round trip. Cheaper, but you may not get filled.

**Slippage** — the market moves against you while your order fills. If the
book is thin (small coins, big size), you pay more. We assume:
- **1 basis point per side** (0.02% round trip) on deep coins like BTC/ETH.
- **5 basis points per side** (0.10% round trip) on small caps.

Realistic total round-trip cost: **0.11% (top coin, taker) to 0.19% (small
cap, taker)**.

## 2. What is "breakeven"?

**Breakeven = the gross edge you need just to not lose money.**

If every trade costs 0.09% round trip, then a strategy whose average trade
makes 0.05% is losing money — the exchange takes more than you make. The
strategy must make **more than 0.09% per trade, on average, before fees** to
survive.

| Cost (round trip) | Breakeven gross edge |
|---|---|
| Maker 0.036% | 0.036% |
| Taker 0.09% | 0.09% |
| Taker + top-coin slippage 0.11% | 0.11% |
| Taker + small-cap slippage 0.19% | 0.19% |

## 3. Why do costs kill edges? An analogy

Think of an edge as a **net you cast into the sea**. The gross edge is the
fish that swim into the net. Costs are **holes in the net** — every trade
that passes through loses a little to fees.

- A **big fish** (daily crash reversion: +2.5% per catch) swims in and barely
  notices the holes. You keep ~2.4% after costs.
- A **small fish** (a 5m bounce: +0.05% per catch) swims in and falls right
  out the holes. Costs eat 0.09% of a 0.05% catch. Net: you paid to go
  fishing and lost money.

Statistical "real" and financial "worth it" are **different questions**. A
pattern can be 100% statistically real (it would only appear by chance once
in 10,000 tries) and still lose you money, because the edge per trade is
smaller than the cost per trade.

## 4. The cost × frequency trap

Costs hurt **each** trade. So the more often you trade, the more the holes
bleed you.

- **Daily crash reversion**: ~13 trades/year. Fees matter little (0.09% on a
  2.5% edge is a rounding error). Rare, chunky, fee-proof.
- **5m scalping**: hundreds of trades/week. Even a tiny 0.09% per trade adds
  up to bleeding the account dry — and each individual edge is often under
  0.09% to begin with.

Rule of thumb: **intraday small edges need to be several times the fee just to
be worth researching; daily big edges can shrug off the same fee.**

## 5. What survived, and what didn't (one sentence each)

- **Survived**: buying after a daily 3σ crash and holding ~5 days. Net
  +2.38% per trade after costs — 26× the fee. (Provisional until the
  out-of-sample backtest, ag-08, confirms it.)
- **Died**: the weekday strategy (lost money even *before* fees — the rule
  traded the wrong day), the 5m post-crash bounce (0.05% edge < 0.09% cost),
  and the 1h body-position reversion (~0.04% edge < 0.09% cost).
- **Not a trade at all, but still useful**: volatility clustering and the
  hour-of-day volatility bump. They don't say *which way* price goes, so you
  can't trade direction on them — but they tell you how *big* moves are
  likely to be. That's a **sizing** tool: trade smaller when volatility is
  spiking.

## 6. The takeaway

Fees and slippage are the **hype filter**. The experiment found plenty of
statistically real patterns, but once you subtract real costs, **almost all of
them are too small to trade.** The one exception is the daily crash reversion,
whose edge is roughly twenty-six times its trading cost. That's the whole
story of this experiment in one number.

And remember: this is history, not advice. Even the survivor is a statistical
observation, not a promise.
