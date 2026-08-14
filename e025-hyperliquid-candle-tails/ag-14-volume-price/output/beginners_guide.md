# Volume, price and direction — a beginner's guide

## Why volume matters

A price chart shows *where* a market traded. **Volume** shows *how much* it
traded. The idea behind this whole experiment is that the two together tell a
story:

- A big price move on **huge volume** = lots of money participating. The move
  may be "real".
- A big price move on **tiny volume** = few people involved. The move may be
  an accident, or a trap.

Traders say volume *confirms* a move. If price goes up and volume is high,
that's "confirmation" — the move has support. If price goes up but volume
stays flat or falls, that's a **divergence** — a warning sign.

This experiment tested whether that intuition actually holds in Hyperliquid
perpetual-futures data, using daily candles for 12 coins.

### The honest catch

We only have **total volume** per candle. Hyperliquid does not report how much
of that volume was buying vs selling. So every signal in this experiment is
built from the OHLCV columns you can see on any chart. Wherever a signal
"should" know up-volume vs down-volume, we approximate it from the price move
(a candle that closed up counts its volume as "up volume").

Also — and this is the most important lesson of the whole e025 experiment —
trading costs money. Every time you buy and sell you pay a fee
(Hyperliquid taker: 0.045% per side = 0.09% round trip). Any edge smaller than
that is eaten alive. Most statistical patterns in crypto are smaller than the
fee.

## The 5 signals, in plain language

### 1. Move × volume (does high volume make moves continue?)

Take each daily candle. If it closed up, call it an "up move"; if it closed
down, a "down move". Then rank that candle's volume against all other candles
of the same coin (percentile 1–100).

The classic theory: an up move on top-1% volume should *continue* up tomorrow
(volume confirms direction).

**What we found: it does not.** An up day on the biggest volume followed
about the same as an up day on quiet volume (next-day returns +0.09% vs
+0.20%). The most interesting wrinkle was the opposite corner: down-days on
enormous volume bounced *up* the next day (+0.36%), which looks like panic
selling followed by relief. But the sample in that extreme bucket is so small
per coin that we can't claim it as a real pattern.

### 2. OBV divergence (the "is the move healthy?" test)

**On-Balance Volume (OBV)** is a running total: start at 0, add the candle's
volume on up days, subtract it on down days. If OBV trends up, money is
flowing in; if down, money is flowing out.

We look at the *slope* of OBV over the last 10 days and the slope of price
over the same 10 days, then combine:

| Price | OBV | Meaning | Next-day mean return |
|---|---|---|---|
| up | up | confirmation — healthy rally | +0.24% |
| up | down | **bearish divergence** — rally not confirmed | −0.10% |
| down | up | bullish divergence — selloff not confirmed | −0.03% |
| down | down | confirmation — healthy selloff | +0.15% |

**This was the strongest result in the experiment.** When price went up but
OBV went down (bearish divergence), the next day was on average *negative*
(−0.10%), and 5 days later −0.15%. When both went up together, the next day
was +0.24% and 5 days later +0.96%. That's a 0.34pp gap on the next day and
1.11pp over five days, and it held in 8 of 10 coins and in both halves of the
sample.

The catch: a short position entered after a bearish divergence earns about
+0.10% before fees. After the 0.09% round-trip cost, that's a rounding error.
It's real, but it's not a meal.

### 3. VWAP distance (is price stretched too far?)

**VWAP (Volume-Weighted Average Price)** is the average price where volume
actually traded over the last 20 days, weighted by how much traded at each
price. Think of it as "where the market really agreed on a price".

We measure how far the current price is above or below VWAP, in units of
standard deviation.

The classic theory: price stretched far above VWAP (everyone who bought is
profitable, so they'll sell) should *fall back* toward it — mean reversion.

**What we found: it doesn't.** Price stretched above VWAP kept drifting up,
and the two halves of the data disagreed. Honest null: on this data, distance
from VWAP tells you nothing reliable about direction.

### 4. Up/down volume ratio (who's been winning the last 10 days?)

Over the last 10 candles, add up volume on up days and volume on down days,
then divide. A ratio of 3 means three times as much volume happened on up
days.

The theory: if buyers have been dominating for 10 days, the trend should
continue.

**What we found: nothing replicable.** The gap between the most-up-volume
buckets and the most-down-volume buckets flipped sign between the two halves
of the data. Null.

### 5. Volume-adjusted return (was that move "earned"?)

Divide a candle's return by its volume relative to the coin's normal volume:

    move per unit of volume = return / (candle volume / median volume)

A **high** value means: the move happened on unusually *little* volume for its
size. A **low** value means: it took a lot of volume to make that move.

**What we found:** a down move that happened on unusually low volume for its
size **reverted upward** — the next day was +0.24% on average (and +1.27%
five days later), versus −0.13% for a down move that happened on heavy volume.
This held in 6 of 9 coins and in both halves.

This makes intuitive sense: if price fell hard but almost nobody traded, the
move wasn't real — the market gives it back. It's the same pattern as the
daily-crash reversion found earlier in e025 (ag-07/ag-08). It's the only
signal here that beats the 0.09% fee with room, and even then only on the
5-day horizon (+1.18pp net).

## The three big takeaways

1. **Divergence is the real signal.** Price rising while OBV falls is a
   warning, and price falling on no volume is a gift. Volume *contradicting*
   price is informative; volume *agreeing* with price is not.

2. **The classic "volume confirms direction" is weak here.** The headline
   hypothesis of this phase — up moves on high volume continue — simply does
   not show up in daily Hyperliquid data.

3. **Fees eat almost everything.** Two of five signals were statistically
   real. Only one — buy after a down-move on unusually low volume, hold 5
   days — clears the 0.09% round-trip cost with room. Everything is measured,
   nothing is assumed to be tradeable.

## How to read the numbers in `signals.csv`

Each row is one bucket of one signal. The columns:

- `n` — how many candles landed in this bucket
- `ret_next1_mean` / `ret_next1_median` — average / typical return of the
  *next day* (in %). Positive mean + negative median is normal for crypto: a
  few big up days pull the average up.
- `ret_next1_win` — fraction of next-days that were positive
- `ret_next5_mean` — average return over the next 5 days
- `h1_*` / `h2_*` — the same stats on the first and second half of the data,
  so you can check the pattern wasn't a fluke of one period

Rows with `coin = ALL` pool all 12 coins. Other rows are per-coin.

**A pattern is only real if it repeats in both halves of the data AND in a
majority of coins.** That's the standard used in this experiment — anything
else is likely noise.
