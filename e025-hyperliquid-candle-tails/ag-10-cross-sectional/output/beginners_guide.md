# Beginner's Guide: Cross-Sectional Analysis

This guide explains the three questions we asked about 12 cryptocurrencies,
how we tested them, and what the results mean — in plain English.

---

## What is "cross-sectional" analysis?

Most of our earlier experiments looked at **one coin at a time** (does BTC
have a pattern? does ETH?). Cross-sectional analysis compares **all coins to
each other on the same day**. Think of it like a class ranking: instead of
asking "how did Johnny do on the test?", you ask "who scored highest today,
and do high scorers tend to stay high?"

---

## Q1: Relative Strength (Momentum)

### What we asked

If a coin has been going up recently, is it likely to keep going up? What
about coins that have been going down?

### How we tested it

1. **Rank the coins**: Every day, we calculate how much each coin gained (or
   lost) over the past 5 days and past 20 days. Then we sort them from
   best to worst.

2. **Make buckets**: The top 3 performers go in the "winners" bucket. The
   bottom 3 go in the "losers" bucket. The middle 6 go in the "middle"
   bucket.

3. **Check the future**: We look at what happened the next day and the next
   5 days for each bucket. Did winners keep winning? Did losers keep
   losing?

### What we found

- **Winners beat losers**, but not by a huge amount. The top 3 coins averaged
  +0.29% the next day, while the bottom 3 averaged +0.06%.
- The gap is bigger over 5 days: top 3 averaged +1.59% vs bottom 3 at +0.56%.
- The pattern **held up** when we checked the second half of the data
  separately (this is called "out-of-sample" testing — using data the
  pattern wasn't discovered on).

### Is this a lot?

The difference is about 0.2-0.4 percentage points per day. Over a year,
that compounds to a meaningful edge. But the day-to-day results are noisy —
some days losers outperform winners. The edge is in the **average**, not
every single day.

### Analogy

Imagine 12 runners in a race. Yesterday, 3 ran fast and 3 ran slow. We're
asking: tomorrow, will the fast runners stay fast? The answer is "slightly
yes" — but it's not a guarantee.

---

## Q2: Long-Short Portfolio

### What we asked

If we bet on the winners (buy them) and bet against the losers (sell them
short), do we make money after paying trading fees?

### How it works

- **Going long**: buying a coin hoping it goes up.
- **Going short**: borrowing a coin and selling it, hoping it goes down, then
  buying it back cheaper.
- **Fees**: every time you trade, the exchange takes a cut. On Hyperliquid,
  it's 0.045% per trade ("taker fee"). A long-short position needs 2 trades
  (buy + sell), so you pay 0.09% total per day.

### What we found

- **N=20 strategy**: turned $1 into $4.41 over ~2.5 years, even after fees.
  That's a 341% total return.
- **Sharpe ratio of 1.28**: this measures return per unit of risk. Above 1
  is good. Above 1.5 is excellent. 1.28 is solid.
- **But the drawdown was -66%**: at some point, the strategy lost two-thirds
  of its value. That's terrifying and would be hard to stick with.

### The honest truth

This strategy **works** in our test, but:
- 12 coins is too few for real diversification
- A -66% drawdown means you need a 195% gain just to break even
- Past performance doesn't guarantee future results
- In real trading, slippage (getting a worse price than expected) would eat
  more into profits

### Analogy

Imagine you always bet on the 3 fastest horses and bet against the 3
slowest. On average, you'd win more than you lose. But occasionally all the
fast horses trip at once, and you lose big. The wins add up, but the losses
can be devastating.

---

## Q3: Co-Movement (Do Crashes Hit Everything?)

### What we asked

When one coin has an extreme day (a 3-sigma move — very rare, like a 10%
crash), do the other coins also move in the same direction? Or do they
stay independent?

### What is a "3-sigma" event?

If a coin normally moves 2% per day, a 3-sigma event would be a move of
6% or more (3 times the normal volatility). These are rare — they happen
maybe 1-2 times per year per coin.

### What we found

- **On crash days**: when one coin crashes, **96% of the other coins also
  drop**. That's almost everyone falling together.
- **On surge days**: when one coin surges, **84% of the other coins also
  rise**. Strong, but not as extreme as crashes.
- For comparison, if coins were independent, you'd expect 50% co-movement.

### Why this matters

This tells us that crypto has a **market factor** — a force that pushes all
coins in the same direction. It's strongest during crashes. This means:

1. **Diversification doesn't help much in crashes**. If you hold 10 different
   coins thinking "they won't all drop at once" — they probably will.
2. **Tail risk is systematic**. The worst losses happen to everyone
   simultaneously.
3. **BTC and ETH lead the market**. Their extreme moves predict what
   everything else does.

### Analogy

Imagine 12 boats tied together with ropes. In calm water, they drift
independently. But when a big wave hits, they all crash into each other.
The ropes (correlation) tighten during storms.

---

## Key Concepts Explained

### Out-of-Sample (OOS)

Imagine you study last year's test scores to find a pattern, then predict
next year's scores. If your prediction works on data you've never seen,
that's "out-of-sample" success. It's the gold standard for testing
strategies.

We split our data in half by time. We found patterns in the first half,
then tested them on the second half. If the pattern works on both halves,
it's more likely to be real.

### Sharpe Ratio

A measure of "how much return am I getting for the risk I'm taking?"
- 0 = no return
- 1 = decent
- 2 = excellent
- Above 2 = suspicious (probably too good to be true)

Our long-short strategy has a Sharpe of 1.28, which is solid.

### Drawdown

The biggest peak-to-trough loss. If your portfolio goes from $100 to $34,
that's a -66% drawdown. It matters because most people can't emotionally
handle watching their money lose two-thirds of its value.

### Taker Fees

When you place an order that "takes" someone else's offer off the book,
you pay a taker fee. On Hyperliquid perps, that's 0.045%. Buying and
selling = 0.09% round trip. This sounds small but adds up when you trade
every day.

---

## Summary

| Question | Answer | Should you trust it? |
|----------|--------|---------------------|
| Do winners keep winning? | Slightly, yes | Medium — the effect is real but noisy |
| Can you profit from it? | Yes, +341% over 2.5 years | Medium — huge drawdown, tiny sample |
| Do crashes hit everyone? | Yes, 96% co-movement | High — unambiguous result |

The biggest takeaway: crypto has real momentum (winners keep winning) but
also massive co-movement (everyone crashes together). Diversification
within crypto is limited when you need it most.
