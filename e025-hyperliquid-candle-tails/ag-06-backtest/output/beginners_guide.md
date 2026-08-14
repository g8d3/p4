# ag-06 — The whole pipeline, explained for a beginner

Date: 2026-08-13

This guide walks through the entire experiment step by step. Each concept is
explained with an everyday analogy. If you only read one file, read this one.

## What we are trying to find out

An earlier experiment (ag-05) looked at Hyperliquid 1-day candles and found
something suspicious: on some weekdays crypto prices tend to move **down**
(Monday, Wednesday), and on others they tend to move **up** (Thursday,
Sunday). Median moves were small (−0.4% to +0.3%) but consistent across coins.

Two questions follow, and this experiment answers both:

1. **Is the pattern real, or is it luck?** (Part 1 — permutation test)
2. **Can you make money trading it, after paying fees?** (Parts 2 & 3 —
   strategy spec + backtest)

## Part 1 — The permutation test: is it luck?

**The problem**: if you look at enough data, you will always find *something*
that looks like a pattern, even in pure randomness. The question is whether
the pattern would survive having its labels scrambled.

**The trick — "shuffle the days"**:

Imagine a deck of 7 cards, one per weekday. Deal each of your candles a card
at random. Then ask: does the "Monday is down" pattern still show up when
each candle is assigned a random weekday?

- If yes → the pattern was never about weekdays. It was luck.
- If no → the pattern really does depend on the weekday.

We repeat this scrambling **10,000 times** and count how often a random
shuffle produces a pattern as strong as the real one. That count divided by
10,000 is the **p-value**.

**Reading the p-value**: p = 0.01 means "luck would make a pattern this
strong only 1 time in 100". Our result: **p < 0.0001** — not one random
shuffle out of 10,000 matched the real pattern. The pattern is real, not
luck. We also checked coin-by-coin: 9 of 12 coins show the pattern
individually.

Analogy: if a flipped coin lands heads 9 times out of 10, you'd want proof
it isn't a fair coin. The permutation test is that proof — and the coin is
weighted.

## Part 2 — The strategy spec: the recipe

A strategy spec is a **cookbook recipe** for a robot: exactly what to do on
which day, so there is no improvisation. Three recipes:

- **Rule A** (the idea): short Mon/Wed at the day open, close at day close;
  long Thu/Sun the same way. This is the weekday tilt.
- **Rule B** (the control): the *opposite* bet. If Rule A is a real edge,
  Rule B should do worse. If both do the same, the edge is probably noise.
- **Rule C** (the baseline): just be long the market. Every strategy must
  beat "do nothing / be long" to be interesting.

It also fixes **fees**: Hyperliquid charges 0.045% per side when you take
liquidity (taker), 0.018% per side when you provide it (maker). Every trade
is a round trip (enter + exit), so taker cost is 0.09%, maker 0.036%. These
fees are the silent killer of small edges.

## Part 3 — The backtest: the honest exam

A **backtest** replays history to see what would have happened. But there is
a trap: if you design a strategy by looking at data, and then test it on the
*same* data, of course it looks good — you memorized the answers.

The fix is the **out-of-sample** rule: split each coin's history in half by
time, and only run the strategy on the **second half** — data the strategy
never saw while being designed. That's like studying for an exam with a
practice test, then taking a *different* exam.

The scores we compute:

| Term | Meaning (plain English) |
|---|---|
| **Expectancy** | Average money per trade. Positive = the strategy makes money per bet on average. |
| **Win rate** | Fraction of trades that end green. A coin flip gives ~50%. |
| **Max drawdown** | The biggest dip from a peak to a trough. How scary the ride is. |
| **Sharpe-style ratio** | Reward per unit of risk. Higher = smoother, better risk-adjusted returns. |
| **Gross vs net** | Gross = no fees. Net = after taker or maker fees. Always compare net. |

## What we found (the honest result)

**The pattern is real, but the strategy loses money.**

| Rule | Net taker result | What it means |
|---|---|---|
| A (weekday tilt) | **−85%** total, −0.43%/trade | The idea loses badly, even before fees |
| B (control) | −49% total, −0.08%/trade | The control also loses |
| C (long daily) | −66% total, −0.09%/trade | Just being long every day also loses in this window |
| Buy-and-hold | −7% total | The "do nothing" baseline |

### Why does Rule A lose if the pattern is real?

This is the single most instructive finding. The earlier study measured the
return of the **next** candle (`ret_next`). The strategy trades the **same
day's** open-to-close. Those are **different days**:

- `ret_next` after a **Monday** candle is −0.42% → that loss happens on
  **Tuesday** (Tuesday's own intraday move is −0.56%).
- But the strategy **shorts Monday** — and Monday's own move is **+0.28%**
  (up). Shorting an up day loses.

Every Rule A signal points the trade at the wrong day. The pattern is
real — it just lives one day to the side of where the spec points. We
**deliberately did not** "fix" the spec and re-test, because choosing a rule
after seeing the out-of-sample results is cheating (data snooping). Fixing it
is a job for a follow-up experiment with pre-registered rules.

### The fees caveat

Even the near-break-even numbers (Rule B gross +0.007%/trade) turn negative
after the 0.036% maker fee, and decisively after the 0.09% taker fee.
Nothing here survives fees.

### The correlation caveat

The 12 coins are not 12 independent tests — they all move with BTC. The
"effective" independent evidence is closer to one or two time series, not
12×632 days. Treat the pooled numbers accordingly.

## The one-line summary

The weekday pattern is **statistically real** (p < 0.0001), but as a trading
idea it **fails out-of-sample**: the spec'd strategy loses money even before
fees, because it trades the same day while the pattern describes the next
day. The experiment measured honestly rather than forcing a win.

## Risk warning

This is a statistical exercise on historical data. It is not trading advice,
and past results do not predict the future. A backtest that "works" can still
fail live; one that fails in the backtest is almost certainly dead.
