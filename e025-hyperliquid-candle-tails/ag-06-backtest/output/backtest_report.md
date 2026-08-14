# ag-06 — Part 3: Backtest report (out-of-sample, net of fees)

Date: 2026-08-13
Input: 1d candles, v>0, 12 coins. Trades built per `strategy_spec.md`.
Charts: `backtest_equity.png` (equity + drawdown paths, net taker).

## Plain English

A **backtest** is a time machine for money: we replay the strategy on history
to see what would have happened. The **out-of-sample** rule is the guard
against fooling ourselves: we only run the strategy on the **second half** of
each coin's history — data that was never used to invent the idea. If the
idea only works on the data that inspired it, it's worthless; out-of-sample
is the real exam.

**Expectancy** = the average money made (or lost) per single trade. **Win
rate** = the fraction of trades that end up green. **Max drawdown** = the
biggest loss you would have watched your account fall from a peak before it
recovered — the number that tells you how scary the ride is. **Sharpe-style
ratio** = reward per unit of risk (annualized). **Fees** = the exchange's cut
(taker 0.045% per side, 0.09% round trip).

## Out-of-sample window (exact dates)

Each coin's 1d series is split at its median timestamp; **only the second
half is traded**:

| Coin | OOS start | OOS end | candles |
|---|---|---|---|
| AAVE | 2025-01-29 | 2026-08-13 | 562 |
| BTC | 2024-11-20 | 2026-08-13 | 632 |
| CRV | 2024-12-29 | 2026-08-13 | 593 |
| DOGE | 2024-12-08 | 2026-08-13 | 614 |
| ETH | 2024-11-20 | 2026-08-13 | 632 |
| HYPE | 2025-10-10 | 2026-08-13 | 308 |
| LIT | 2026-04-19 | 2026-08-13 | 117 |
| PUMP | 2026-01-26 | 2026-08-13 | 200 |
| SOL | 2024-11-23 | 2026-08-13 | 629 |
| XMR | 2026-05-01 | 2026-08-13 | 105 |
| XRP | 2025-01-14 | 2026-08-13 | 577 |
| ZEC | 2026-03-09 | 2026-08-13 | 158 |

Global OOS range: **2024-11-20 → 2026-08-13** (~21 months, 632 trading days).
Caveat: the newest coins (LIT, XMR, ZEC) have very short second halves
(105–200 candles) — their per-coin numbers are noisier.

## Pooled results (equal weight across coins per day)

The pooled view treats every coin equally each day: each day's return is the
mean of that day's per-coin trade P&Ls. This is the "market-pooled" number.

| Metric | Rule A (tilt) | Rule B (control) | Rule C (long daily) |
|---|---|---|---|
| Trades | 2,938 | 5,127 | 5,127 |
| **Total return (net taker)** | **−85.4%** | **−48.5%** | **−66.2%** |
| **Expectancy net taker** | **−0.430% / trade** | **−0.083% / trade** | **−0.094% / trade** |
| Expectancy net maker | −0.376% / trade | −0.029% / trade | −0.040% / trade |
| Expectancy gross (no fees) | −0.340% / trade | +0.007% / trade | −0.004% / trade |
| Win rate gross | 46.4% | 50.6% | 48.0% |
| Win rate net taker | 45.0% | 49.2% | 46.6% |
| Max drawdown (net taker) | −89.5% | −67.2% | −74.8% |
| Sharpe-style (daily, ann.) | −1.74 | −0.21 | −0.56 |

**Buy-and-hold benchmark (pooled): gross −6.8%, net taker −6.9%.**

## Per-coin results (net taker, equal notional per coin)

| Coin | A total | B total | C total | A exp/trade | B exp/trade | C exp/trade | A win | B win | C win |
|---|---|---|---|---|---|---|---|---|---|
| AAVE | −87.1% | −59.1% | −81.1% | −0.52% | −0.05% | −0.18% | 47% | 49% | 46% |
| BTC | −72.7% | −60.5% | −60.7% | −0.33% | −0.12% | −0.12% | 44% | 46% | 47% |
| CRV | −96.5% | −91.4% | −85.8% | −0.83% | −0.27% | −0.19% | 41% | 48% | 45% |
| DOGE | −85.8% | +143.7% | −91.1% | −0.46% | +0.24% | −0.30% | 44% | 54% | 43% |
| ETH | −87.9% | −61.5% | −65.1% | −0.51% | −0.08% | −0.10% | 42% | 50% | 49% |
| HYPE | −77.6% | −81.2% | −1.8% | −0.73% | −0.41% | +0.12% | 46% | 47% | 50% |
| LIT | −14.9% | −15.5% | +113.8% | −0.03% | +0.09% | +0.88% | 60% | 50% | 55% |
| PUMP | −15.9% | −51.9% | −4.4% | 0.00% | −0.21% | +0.12% | 48% | 49% | 50% |
| SOL | −71.1% | −3.9% | −83.1% | −0.26% | +0.08% | −0.20% | 48% | 51% | 47% |
| XMR | −20.8% | −50.6% | −5.7% | −0.32% | −0.58% | +0.03% | 52% | 47% | 52% |
| XRP | −76.8% | −59.2% | −76.1% | −0.35% | −0.07% | −0.17% | 43% | 50% | 44% |
| ZEC | −14.0% | −53.4% | +112.7% | +0.06% | −0.26% | +0.70% | 47% | 47% | 49% |

## The verdict: the pattern is real, but the spec'd strategy trades the wrong day

This is the most important result of the experiment, and it is honest rather
than pretty: **Rule A loses money out-of-sample, even before fees.**

Expectancy per trade is **−0.34% gross** for Rule A. Compare the fee model:
0.09% round trip. Rule A is not killed by fees — it loses **3.8× the fee
cost per trade** before any fee is charged. The control (Rule B) and baseline
(Rule C) also lose or barely break even. Fees are not the reason this idea
fails; the edge simply isn't where the spec points.

### Why — the one-day shift (the pitfall from the spec, proven)

ag-05 measured the pattern on `ret_next` — the return of the **next** candle.
The strategy spec instead trades the **same day's** open→close. For 1d
candles these two definitions are shifted by one weekday, and the table below
(OOS data) shows exactly where the money lives:

| Open day | intraday (c−o)/o median | ret_next median | Spec says |
|---|---|---|---|
| Mon | **+0.28%** | −0.55% | SHORT Mon |
| Tue | −0.56% | −0.09% | — |
| Wed | −0.08% | **−1.10%** | SHORT Wed |
| Thu | **−1.10%** | +0.02% | **LONG Thu** |
| Fri | +0.03% | +0.05% | — |
| Sat | +0.04% | −0.20% | — |
| Sun | −0.16% | +0.28% | LONG Sun |

Read the columns **horizontally**, not diagonally:

- `ret_next` says "Monday-open candles are followed by a −0.42% move" — that
  move happens on **Tuesday**, not Monday. Tuesday's own intraday is indeed
  down (−0.56%).
- The spec turns this into "short Monday" — but **Monday's own intraday is
  UP (+0.28%)**. Shorting it loses.
- Same for Thu: `ret_next` after Wed-open candles is −0.60% (realized on
  **Thursday**, which is −1.10% intraday), yet the spec **longs** Thursday.

Rule A systematically takes the **opposite side** of the same-day move. That
is why every per-coin total for Rule A is negative. The weekday pattern
discovered in Part 1 is statistically real — but it is a **next-day** pattern,
and the rulebook pointed the trades at the wrong day.

### Would the "corrected" version make money? We deliberately did NOT test it.

Fixing the spec to trade the day the return actually lands (e.g. short
Tue/Thu, long Fri/Mon) would be choosing the rule **after** seeing the
out-of-sample results — that is the exact form of data snooping this
experiment was designed to catch. It belongs in a **follow-up experiment**
with its own pre-registered rules, not in this report. Reporting Rule A's
failure here is the honest outcome; "the pattern is real but the strategy as
written doesn't capture it" is a valid and useful result.

### Fee sensitivity

Even the per-trade numbers that are *closest* to zero — Rule B gross
(+0.007%) and Rule C gross (−0.004%) — are turned negative by the 0.036%
maker round trip and more so by the 0.09% taker round trip. Nothing in this
test survives fees at either rate.

### Correlation caveat

The pooled numbers treat every trade as an observation, but the 12 coins are
highly correlated (they are all crypto perps moving with BTC). The effective
independent sample is much smaller than 12× the trades. Do not quote "12
coins × 632 days ≈ 7,600 trades" as if they were independent — they are not.
Treat the pooled result as roughly **one or two independent time series**
worth of evidence, not twelve.

## Risk caveat

This is a statistical exercise on historical data, not trading advice. Past
results do not predict future results. A strategy that "works" in a backtest
can still fail live, and this one did not work even in the backtest.

## Bottom line

- **Part 1**: the weekday pattern is statistically real (permutation
  p < 0.0001, 9/12 coins pass individually).
- **Part 3**: the strategy built from it loses money out-of-sample (Rule A
  −85% net, expectancy −0.43%/trade, even gross is −0.34%/trade) — because
  the spec trades the same-day intraday while the finding described the
  **next-day** move. No rule, control, or baseline beats buy-and-hold in this
  window, and nothing survives fees.
- The experiment's job was to measure, not to make the strategy look good.
  Measured honestly, the weekday direction edge **does not transfer** to the
  intraday strategy as specified.
