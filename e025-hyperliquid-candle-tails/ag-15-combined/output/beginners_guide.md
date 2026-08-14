# ag-15 — A beginner's guide to combining signals

## The whole idea in one picture

Two earlier experiments found that when a coin's price falls in a certain way,
it tends to *bounce back* over the next 5 days. This phase asks: can we use
**both** signals at once to get more chances to catch that bounce?

Imagine you're fishing with two different lures:

- **Lure A (the "crash")**: the fish bit after a dramatic one-day fall.
- **Lure B (the "quiet drop")**: the fish bit after a fall that happened on
  unusually *little* trading volume for how big the fall was.

Both lures worked separately. This experiment just throws **both** in the water
at the same time and counts how many more fish you catch.

## The two signals, in plain words

**Signal 1 — "the crash" (T1).** Each coin has a "usual daily wobble" — how much
its price moves on a normal day. When a coin drops more than **three times its
usual wobble** in one day, that's a crash. The earlier work showed crashes are
usually followed by a bounce.

**Signal 2 — "the quiet drop" (T2).** When a coin falls, but the fall happened
on *surprisingly little volume* — not many people were trading — it turns out
those falls also tend to bounce. It's like the fall was a mistake that the
market later corrects.

**The sneaky bit:** we only let the rules "learn" from the FIRST HALF of each
coin's history, then we test them on the SECOND HALF. This is called
**out-of-sample** testing. It stops us from fooling ourselves — the rules are
judged on data they never saw while being designed.

## The five rules

| Rule | What it does |
|---|---|
| **A** | Buy after a crash. Wait 5 days, sell. |
| **B** | Buy after a quiet drop. Wait 5 days, sell. |
| **C** | Buy after **a crash OR a quiet drop**. Wait 5 days, sell. |
| **D** | Buy only when it's **a crash AND a quiet drop** at the same time. |
| **E** | The "do nothing smart" baseline: just always own the coins. |

Everything is real-world: you pay a fee to buy and a fee to sell (0.09% round
trip), you can only own one position per coin at a time, and no leverage.

## What we found

**1. Pooling works — you get 11× more trades.**
The crash-only rule (A) found **28** chances in the unseen data. The combined
rule (C) found **312** — eleven times more, spread over 155 different days
instead of just 8. And it still made money after fees: about **+0.55% per
trade**. The best part: 312 trades is a much more trustworthy sample than 28.
A few big numbers are easy to fool; 300+ are harder.

**2. The volume filter does NOT make crashes better.**
We tested the "purest" version — a crash that ALSO happened on low volume (rule
D). It lost money (−0.54% per trade) and only happened 20 times. So the idea
"quiet crashes bounce back the hardest" is **not supported** by the data. If
anything, the 8 crashes that happened on *normal* volume were the ones that
bounced (+5.7% each, all 8 won). But 8 is a tiny number, so that's a hint for
future work, not a discovery.

**3. The two signals are mostly different things.**
Only **4%** of the quiet-drop signals were also crashes. So rule C isn't
cheating by double-counting the same events — it's genuinely adding new
opportunities.

**4. In numbers, after fees (taker):**

| Rule | Trades | Avg profit/trade | Win rate | Total return |
|---|---|---|---|---|
| A — crash only | 28 | +1.24% | 68% | +3.6% |
| B — quiet drop only | 308 | +0.48% | 48% | +13.5% |
| **C — combined** | **312** | **+0.55%** | 49% | **+16.3%** |
| D — crash AND quiet | 20 | −0.54% | 55% | −1.4% |
| E — always long | 5,123 | −0.10% | 47% | −67.2% |

Notice the baseline (E): just *owning* these coins over this period lost −67%.
All three reversion rules beat that. But also notice B and C win less than half
their trades — they make money from a few big bounces, not from being right
most of the time.

## Honest words of caution

- **Winning less than half the time.** The combined strategy wins only 49% of
  trades. It makes money because the winners are bigger than the losers. That
  means you need to actually hold to day 5 — selling early turns a good system
  into a coin flip.
- **The deep dips.** Rule C's portfolio fell as much as −32% at its worst
  point. That's a hard ride.
- **The 12 coins move together.** When crypto crashes, most coins crash the
  same day. So 312 trades are really fewer *independent* events than they look.
- **One kind of market.** The test window was a bear market. We can't say how
  this behaves in a bull market.
- **Past ≠ future.** This is a statistical exercise on history. It tells you
  what happened, not what will happen. Not investment advice.

## The one-sentence takeaway

Combining the crash signal with the low-volume signal gives you eleven times
more opportunities with the edge still intact — but the "quiet crash" refinement
didn't pan out, and nothing here is a guarantee of future returns.
