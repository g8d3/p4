# Beginners guide: event study, 3σ, pivots, no-lookahead, MAE/MFE

This guide explains the ideas behind `ag-07` in plain words. If you understand
this page, you can read `report.md` without getting lost.

---

## Where this fits in the whole experiment

`e025` is a series of questions about Hyperliquid candles (candles = the
classic open/high/low/close bars). The experiment worked like a pyramid:

1. **ag-01** downloaded the raw candle data (once — all later agents reuse it).
2. **ag-02** measured how price *moves*: distributions, fat tails.
3. **ag-03** asked: is an extreme move *predictable* from the previous candle?
4. **ag-05** asked: do calendar time and volume change the next candle?
5. **ag-06** backtested a strategy based on what was found.
6. **ag-07 (this one)** — an **event study**. Instead of asking about every
   candle, we isolate the *rare* candles (moves bigger than 3σ) and study what
   surrounds them: what was happening before, and what happens after.

Why an event study? Because the previous agents found that "extreme candles are
followed by wider moves" (volatility clustering), but that says nothing about
*direction*. The event study is the right tool for the direction question: when
something dramatic happens, does price keep going (momentum) or snap back
(reversion)?

---

## What is 3σ?

Imagine you list a coin's 5-minute percentage moves. They scatter around 0 with
some typical width. **σ (sigma)** is a number that measures that width — the
"standard deviation". Roughly:

- about 68% of moves are within ±1σ of the average,
- about 95% within ±2σ,
- about 99.7% within ±3σ — **if** the data were a perfect bell curve.

So a **3σ move** means "a move 3 typical-widths away from the average": rare,
on the order of 1 in 370 candles for a bell curve.

But crypto is not a bell curve. Prices can jump much more violently than a
normal distribution allows (these are called **fat tails**). In our data,
3σ moves happen on ~1.2–1.9% of candles (not 0.27%) precisely *because* of fat
tails. That's why we compute σ **per coin and per timeframe** — a 3σ move for
BTC is a different size than a 3σ move for a meme coin. "3σ" always means
"unusual for *this coin*", which is exactly the meaning we want.

An **event** = one candle whose move is bigger than 3σ in absolute value, in
either direction. A "3σ up event" is a candle that shot up 3σ; a "3σ down
event" is a crash.

---

## What is a pivot / swing high-low?

A **swing high** (also called a pivot high) is a local top: a candle whose high
is higher than the highs of the 5 candles before it **and** the 5 candles after
it. Picture a mountain — the swing high is the peak of the mountain. A **swing
low** is the valley between two peaks.

Swing highs and lows are how traders decide "where is the last important
resistance/support". Our new feature asks: *how far above the last swing high
(or below the last swing low) is the current price, measured in σ units?* We
call this the **swing distance**, and it's the user's requested column:
- `dist_high` positive = price is above its last swing high (extended upward),
- `dist_low` negative = price is below its last swing low (extended downward).

Measured in σ units, these numbers are comparable across coins and timeframes,
which is the whole point of normalizing.

---

## What is no-lookahead, and why does it matter?

**No-lookahead** means: never use information that wasn't available at the time
you'd be making a decision. It is the difference between a fair test and a
magic trick.

In this study there are two no-lookahead rules:

1. **Pivots are only "confirmed" after 5 candles.** A candle might look like a
   swing high at first, but you can't know it's a peak until 5 candles *after*
   it have happened. So when we compute the swing distance at time `t`, we only
   use pivots whose confirmation happened at or before `t`. If we peeked at the
   5 future candles to decide a pivot "early", we'd be cheating — a pattern
   that only works with future information can't be traded.

2. **Pre-event predictors never use event data.** Everything we test as a
   "predictor" (extension, volume, regime, hour) is measured *on or before* the
   event candle. The *outcomes* (what happens after) use the future, which is
   fine — that's the thing we're trying to predict.

Why does this matter? Because most "amazing backtests" you see online die from
lookahead bias: they quietly use tomorrow's data to predict tomorrow. The
replication checks in this study exist specifically to catch that kind of
phantom signal. If a "pattern" doesn't survive seeing half the data after the
fact, it was probably noise (or hindsight).

---

## What are MAE and MFE?

Standing at the moment the event candle **closes**, imagine you enter a trade
right there. Over the next 10 candles:

- **MFE — Max Favorable Excursion**: the best the price is in your favor during
  that window (the best possible exit). It's the *upside* you could have caught.
- **MAE — Max Adverse Excursion**: the worst the price goes against you (the
  worst drawdown you'd have suffered before it came back). It's the *risk* you
  actually had to sit through.

Together they form the "risk envelope" of trading the event. In the report we
quote the median and the 90th percentile of each. Example: a 1d down event has
median MAE −9.3% and median MFE +14.2% — on average, if you buy the day after a
crash you'd first ride a dip of about 9%, but within 10 days you'd usually have
been up ~14% at some point. That asymmetry (upside bigger than downside) is the
signature of mean reversion.

---

## The two big ideas behind the answers

**1. Momentum vs reversion.** After a 3σ move, does price continue in the same
direction (momentum) or snap back (reversion)? We measure this by averaging the
cumulative return over the next 1, 3, 5 and 10 candles, separately for up and
down events. The report's headline: at 5m and 1h — nothing special, pure noise.
At 1d — crashes bounce back (reversion), and that's the only effect that
replicates.

**2. Asymmetry.** "Crashes are the mirror of rallies" sounds plausible but is
usually wrong. In our data rallies are more frequent and slightly bigger than
crashes, but crashes are the ones that revert. If you only studied one side you
would get a misleading picture — which is why the study reports both, always.

---

## Why "replication" is the honesty filter

With ~1000 events per short timeframe, a coin's "average next move" bounces
around by chance. The experiment has a strict rule: **a finding is only real if
it shows up in both halves of the data** (split by time, per coin). Almost
every pattern in this study failed that test — and that is a *result*, not a
failure of the study. It tells us the honest conclusion: after a 3σ event on
Hyperliquid, the next candle is essentially a coin flip, except for the
daily-crash mean reversion. Knowing what does *not* work is exactly what keeps
you from losing money on a phantom edge.
