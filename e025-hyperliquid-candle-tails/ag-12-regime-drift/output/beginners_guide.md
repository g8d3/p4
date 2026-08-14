# Beginners guide: "regime drift" and "stationary"

For someone who has never seen statistics on crypto candles.

## The question in plain English

Imagine you are a fisherman who has kept a log of how big the fish are, year by
year. One year the lake gives you small fish, another year huge fish. Two
questions:

1. **Stationary** — is the lake *the same lake* over time? If you describe it
   once ("average fish is 30 cm"), will that description stay roughly true next
   year? If yes, the lake is "stationary". If the average drifts from 20 to 60
   to 25 cm, the lake is **not stationary**.
2. **Regime drift** — *why* does it change? Lakes don't change by themselves;
   they change because of droughts, seasons, newcomers. In markets we call
   those external conditions "regimes" — calm periods, stormy periods, bubbles.
   "Regime drift" just means the market's behavior wanders because it is
   spending time in different regimes.

## Why this matters before you trade

Every previous experiment in e025 found patterns in candles: fat tails
(extreme moves are more common than a bell curve predicts), a weekday tilt
(Monday/Wednesday weak, Thursday/Sunday strong), crash-reversion (after a huge
down day, the next 5 days tend to be positive).

But there is a hidden assumption in all of them: **that the data behaves the
same way in 2023 as in 2026.** If the market was calm in 2023 and wild in 2024,
then a pattern measured on "average of everything" might be describing mostly
2024 — and silently stop working in 2026. This experiment exists to check that
assumption. A pattern that survives regime changes is trustworthy; one that
only shows up in one era is an illusion.

## What we did (very simply)

1. Cut each coin's history into **quarters** (3-month blocks). 15 quarters for
   the coins with the longest history.
2. In each quarter, measure: how wild the daily moves were (volatility), how
   fat the tails were (kurtosis), how often extreme 3σ moves happened, and
   whether the weekday pattern and the crash-reversion pattern were present.
3. Ask: do these numbers wander quarter to quarter?

## What we found, in one picture

**Some things drift, some things don't.**

- **Volatility drifts — a lot.** Daily moves ranged from about 2% typical
  (quiet quarters) to 6% (wild quarters like late 2024). If you size your bets
  for "average" volatility you will be wrong half the time. This is the
  classic sign of a non-stationary market.
- **Fat tails do NOT drift.** In all 15 quarters, extreme moves were far more
  common than a bell curve says they should be. The *size* of the extremes
  changed with volatility, but their *rarity* was constant. This is the most
  stable fact in the whole experiment.
- **The weekday pattern is the least stable thing we looked at.** Some
  quarters it behaves as expected (Thursday up, Monday down), most quarters it
  doesn't — it even flips upside down in 2026. It only looks solid when you
  average 3.5 years together, which hides the sign-flipping.
- **Crash reversion mostly survives.** After a big daily crash, the next 5
  days were positive in 8 of the 10 quarters that had any crashes. It failed
  exactly in the quarters when the *whole market* was falling — a crash there
  just joined the decline.

## The takeaway in one sentence

**Volatility and how often extreme moves happen change with the market mood —
but the market's fat tails and the tendency to bounce back after daily crashes
are stable across regimes, while the weekday pattern is not.**

## What "stable" means for you

- If a strategy assumes a fixed volatility level, it will over-risk in calm
  quarters and under-risk in wild ones. Use volatility that adapts (this is
  what the volatility-model agent, ag-11, builds).
- Trust a finding more if it survives regime changes (crash reversion: yes).
- Trust a finding less if it only exists in the full-sample average (weekday
  tilt: no — it flips by quarter).
