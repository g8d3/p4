# ag-08 — Out-of-sample backtest: daily crash reversion

Phase 5a of e025. This is the honest, fees-included test of the ONE robust
directional finding from ag-07: **after a daily 3σ down candle, the next 5
days have positive expected return.** Everything here was decided before the
OOS window was ever computed (the grid is fixed — no tuning after seeing
results, the ag-06 lesson).

---

## Plain English (first, as required)

**What we are testing.** ag-07 found that when a coin drops more than 3σ in a
single day (a "crash" — σ is that coin's own daily swing), the following 5 days
tend to be *up*, not down. That is surprising: our first instinct after a crash
is that things keep falling. The data said the opposite. But ag-07 measured
this on the *same* data it used to discover the pattern. Finding a pattern and
then testing it on the same data is like asking the class clown to grade their
own exam.

**What "out-of-sample" (OOS) means.** This backtest only uses the **second
half** of each coin's history to trade, and the 3σ threshold is computed
**only from the first half**. The second half never influenced the rule. If the
edge is real, it should show up in data the rule never "saw" during its design.

**What we compare.** We run three strategies side by side:

- **Rule A (the finding)** — buy at the close of a crash candle, hold 5 days.
- **Rule B (control)** — the mirror image: buy at the close of a +3σ *rally*
  candle, hold 5 days. If buying crashes works *because* it is crashes (not
  because any extreme move bounces), Rule B should behave differently.
- **Rule C (baseline)** — simply being long every day. Is Rule A better than
  just holding the coin?

**Fees are real.** Crypto exchanges charge you to trade. We show everything
*gross* (no costs) and *net* of a taker fee of 0.045% per side (0.09% per
round trip) and a maker fee of 0.018% per side.

**Bottom line, in one paragraph.** In the never-before-seen half of the data,
buying 5 days after a crash made a small positive amount of money net of fees
(+3.6% total over the window, mean +1.24% per trade, 68% of trades profitable),
while buying 5 days after a *rally* lost money (−18%), and simply being long
lost a lot (−67%) because the test window was a bear market. The asymmetry the
finding predicted is visible and in the right direction. **But** there are only
**28 crash trades**, and they collapse to just **8 distinct crash days** shared
across coins — so this is *directional* evidence, not a proof. We say that
clearly below.

---

## Rules under test (the fixed grid — not tuned)

| Rule | Entry | Hold | Exit | Purpose |
|---|---|---|---|---|
| **A** | close of 1d candle with `ret < −3σ` (crash) | **5** daily candles | next close | the ag-07 finding |
| **B** | close of 1d candle with `ret > +3σ` (rally) | 5 | next close | control — is it crashes specifically? |
| **C** | every day | 1 | next close | baseline — always long |
| A-sens | close of crash candle | **3** and **10** | next close | sensitivity (report only, not optimized) |

Equal notional per coin, no leverage, **no re-entry while a position is open**
(single-position rule per coin). The crash candle's own return is **not** part
of the trade — we enter at its close and measure what happens *after*.

**Return definition** (exact): for a trade entered at the close of candle `t`
and held `H` candles, `P&L = (close[t+H] − close[t]) / close[t]`. In per-trade
terms that is Rule A's mean P&L; in time terms it is compounded into the
portfolio equity curve day by day. Fees are applied multiplicatively at both
entry and exit: `net = (1+gross) × (1−fee) × (1−fee) − 1`.

**Walk-forward σ (the core of the OOS discipline):** per coin, `σ = stdev(ret)`
is computed **only on the first half** of that coin's 1d series (the 
`ret = (c[t]−c[t−1])/c[t−1]` series, `v=0` pre-listing candles dropped).
That first-half σ is then used to flag crash/rally candles **in the second
half**. The second half has never contributed to any parameter of the rule.

---

## Out-of-sample window

- Per coin, the OOS window is the **second half by time** of its real 1d
  series (v>0 candles only).
- Pooled window: **2024-11-19 → 2026-08-13** (per-coin OOS starts range from
  2024-11-19 for BTC/ETH up to 2026-04-30 for XMR; all end 2026-08-13).
- Number of OOS trades: **Rule A = 28**, Rule B = 34, Rule C = 5,123 (one per
  day per coin), sensitivity hold-3 = 30, hold-10 = 25.
- ⚠️ **28 < 30** — per the pre-declared rule, this is below the minimum sample
  we said we needed, so the conclusion is **downgraded** to directional
  evidence. It also *collapses further*: the 28 trades happen on only
  **8 distinct calendar days** (7 coins crashed on 2025-03-03, 6 on
  2025-10-10, 6 on 2026-02-05). Crypto crashes are market-wide, so these are
  closer to **8 independent observations than 28**. Keep that in mind for
  every number below.

Per-coin OOS windows and first-half σ are in `output/oos_windows.csv`.

---

## Results — metrics table

All portfolio-level metrics are on the **market-pooled** series: for each
calendar day, the mean return across the coins alive that day (each coin gets
equal weight; a coin with no position that day contributes 0). This is the
honest "what would the portfolio of all 12 coins have done" view.

### Portfolio metrics (gross AND net of fees)

| Rule | Total return gross | Total net (taker) | Total net (maker) | Expectancy net (taker) | Win rate net (taker) | Max DD net (taker) | Sharpe (taker) |
|---|---|---|---|---|---|---|---|
| **A — crash, hold 5** | **+3.91%** | **+3.58%** | **+3.78%** | **+1.24%** | **67.9%** | **−9.03%** | **0.22** |
| **B — rally, hold 5** | **−18.01%** | **−18.36%** | **−18.15%** | **−4.81%** | **17.6%** | **−18.82%** | **−0.78** |
| C — always long | −42.22% | −67.24% | −53.95% | −0.10% | 46.6% | −75.62% | −0.59 |
| A sens. hold 3 | +27.02% | +26.58% | +26.85% | +6.73% | 83.3% | −3.82% | 1.22 |
| A sens. hold 10 | +9.55% | +9.25% | +9.43% | +3.24% | 68.0% | −13.37% | 0.38 |

Definitions: **Total return** = the pooled portfolio's compounded return over
the full OOS window. **Expectancy** = mean P&L per trade (net). **Win rate** =
fraction of trades with positive P&L (net). **Max drawdown** = worst peak-to-
trough decline of the pooled equity curve (net). **Sharpe-style ratio** =
mean daily pooled return ÷ std of daily pooled returns × √365 (annualized
"risk per unit of return" — higher is better; it is NOT a true trade Sharpe).

### Trade-level metrics (per trade, all fee variants)

| Rule | n trades | Mean gross | Mean net taker | Mean net maker | Win gross | Win net taker |
|---|---|---|---|---|---|---|
| A — crash, hold 5 | 28 | +1.33% | +1.24% | +1.29% | 71.4% | 67.9% |
| B — rally, hold 5 | 34 | −4.73% | −4.81% | −4.76% | 17.6% | 17.6% |
| C — always long | 5,123 | −0.010% | −0.100% | −0.046% | 47.8% | 46.6% |
| A sens. hold 3 | 30 | +6.83% | +6.73% | +6.79% | 83.3% | 83.3% |
| A sens. hold 10 | 25 | +3.33% | +3.24% | +3.29% | 68.0% | 68.0% |

Fees model: **taker 0.045% each side (0.09% round trip)**; maker 0.018% each
side (0.036% round trip). Rule C pays a round trip *every day* — that is why
its gross/net gap is large (the baseline is honest, and it hurts).

---

## What the numbers say

1. **Rule A vs Rule B — the asymmetry is real in the OOS window.** Buying
   crashes made money (+1.24% expectancy, 68% wins) while buying rallies lost
   money (−4.81% expectancy, 18% wins). The mirror-image trade is not a mirror
   of the profit — it is a *loss*. This is exactly what ag-07 predicted and the
   reason the control exists: the effect is specific to crashes, not to
   "extreme moves bounce".

2. **Rule A vs Rule C — crashes beat just being long.** Being long the whole
   window lost −67% net (it was a brutal bear market in this window: BTC fell
   ~92k→63k, SOL ~257→76). Rule A made +3.6% in the same period by only being
   in the market for ~40 trading days. Rule A did not make a fortune, but it
   was positive while the passive baseline was deeply negative — the crash
   entries *were* the edge.

3. **Fees do not kill the finding.** The per-trade edge (+1.33% gross) is
   ~15× the 0.09% round-trip taker cost. Even net of taker fees the expectancy
   stays +1.24% and the win rate stays 68%.

4. **Sensitivity (reported, not tuned).** Hold 3 looks better (+6.7%/trade,
   83% wins) and hold 10 is still positive (+3.2%). We did **not** switch to
   hold 3 — the grid was fixed before the test. These numbers are context for
   future work, not a new recommendation (and hold-3 has even fewer independent
   events).

5. **The honest caveats that cap the conclusion:**
   - **28 trades < 30.** Below our own pre-declared minimum → the verdict is
     **downgraded** to directional evidence.
   - **8 independent crash days.** The 12 coins move together; the 28 trades
     are really ~8 market events. The effective sample is small, so the
     confidence intervals around +1.24% are wide.
   - **One regime.** The OOS window is a single (bear) market regime. We
     cannot say how this behaves in a bull regime from this data alone.
   - Rule B's win rate (17.6%) is *more* impressive-looking than Rule A's in
     the other direction — but both come from the same tiny sample of days.

---

## Per-coin results (Rule A, hold 5 — the finding)

| Coin | OOS trades | Mean gross | Mean net (taker) | Win rate (net) |
|---|---|---|---|---|
| AAVE | 5 | +4.46% | +4.37% | 80% |
| BTC | 2 | +4.72% | +4.63% | 50% |
| CRV | 4 | +0.48% | +0.39% | 75% |
| DOGE | 3 | +0.93% | +0.84% | 67% |
| ETH | 6 | −4.81% | −4.90% | 50% |
| SOL | 4 | +1.68% | +1.59% | 75% |
| XMR | 1 | +8.19% | +8.09% | 100% |
| XRP | 3 | +4.89% | +4.79% | 67% |
| HYPE, PUMP, ZEC, LIT | 0 | — | — | — |

**7 of 8 coins** that traded had positive mean net P&L (the same sign in the
OOS window as the ag-07 finding). The lone negative is ETH, dragged down by a
single −25% trade entered 2026-01-31 (a crash that *continued*). Four coins
(HYPE, PUMP, ZEC, LIT) had no crash ≥3σ within their (shorter) OOS windows.

For contrast, Rule B: **0 of 10 coins** that traded had positive mean net P&L.
Every coin's rally-buying lost money out-of-sample.

Full per-coin table: `output/per_coin.csv`. Every trade: `output/backtest.csv`.

---

## Files produced

| File | Contents |
|---|---|
| `output/backtest.csv` | One row per (coin, rule, trade): entry/exit dates, gross + net P&L %, fees |
| `output/backtest_report.md` | this report |
| `output/equity.png` | Equity curves A vs B vs C, net of taker fees (pooled, log scale) |
| `output/oos_windows.csv` | Per-coin OOS date range and first-half σ |
| `output/per_coin.csv` | Per-coin summary for Rule A/B/C |
| `output/equity_daily.csv` | Daily pooled equity index for every rule/fee variant |
| `output/metrics.json` | Machine-readable metrics |
| `output/beginners_guide.md` | This whole pipeline explained for a beginner |
| `output/session-log.md` | What was done and what went wrong |

---

## Verdict

> **The daily-crash reversion survives its out-of-sample, net-of-fees test —
> but as *directional* evidence, not a proof.**
>
> Buying 5 days after a daily crash was profitable net of taker fees
> (expectancy +1.24%, win rate 68%) in the data the rule never saw, while the
> two controls failed in the exact way the finding predicted: buying rallies
> lost money (−4.81% expectancy) and always-long lost a lot (−67%) in the same
> bear-market window. The asymmetry is specific to crashes.
>
> However: only 28 trades (below the pre-declared 30 minimum), collapsing to
> ~8 shared crash days on correlated coins, over a single market regime. That
> is not enough to size a position or call it a proven edge. This is exactly
> what a statistical exercise on history can and cannot tell us — past
> results do not predict the future, and nothing here is trading advice.
