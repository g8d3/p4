# e043 — Course Notes (plain language, for total beginners)

Seed notes for the trading course, written in simple words. Every idea here is
backed by a real backtest in this experiment (`ag-01/output/viz_*.html`).

## The one-page glossary

| Word | Plain meaning |
|---|---|
| **Backtest** | A simulation that replays past price data and answers "how would this plan have done?" |
| **Grid** | A plan that places many buy and sell orders at different prices, like ticks on a ruler |
| **Ladder** | A grid where each "step" is a percentage below/above a reference price |
| **Level** | One step of the ladder: an order with its own price, size, target and stop |
| **Lot** | One piece of capital that runs its own buy → sell → maybe buy-again cycle |
| **Take-profit (V)** | The price where you choose to sell and bank a profit |
| **Stop-loss (SL)** | The price where you choose to sell and accept a loss, so it doesn't grow |
| **Rebuy (R)** | After selling with profit, wait for a dip and buy the same asset again |
| **Regime / state** | The market's current mood, measured from past prices (trending up, down, or just moving sideways = "range") |
| **Range** | Prices bouncing sideways. Grids usually work best here |
| **Trend** | Prices moving one direction for a long time. Grids usually lose here |
| **Anchor** | The reference point the ladder is measured from (e.g. the recent highest price) |
| **Maker fee** | Fee you pay when YOUR order waits at a price and someone else fills it (cheaper) |
| **Taker fee** | Fee you pay when you take someone else's resting order immediately (more expensive) |

## Lesson 1: one number never tells the whole story

We looked at 5 numbers together, not one:

1. **Return %** — did the money grow (compounds everything).
2. **Profit factor** — $ won ÷ $ lost, for the whole test. Simple but blind to
   order, time and compounding.
3. **Max drawdown** — the worst dip. Pain matters: −50% needs +100% to recover.
4. **Sharpe** — return per unit of wobble (risk).
5. **Win rate** — how many trades won. Low win rate can still be profitable if
   wins are big; read it with Profit factor, never alone.

The Profit factor page (`viz_*.html`) shows it *growing trade by trade* and a
calculator you can play with.

## Lesson 2: "buy the dip" sounds smart and loses money (measured)

Backtest on real Bitcoin, 4 years of hourly prices:

- A ladder that "buys when price drops 4–24% below the recent high, sells at
  +5%, stops at −10%" won only ~40% of its trades → lost money.
- Why: a "dip" more often keeps falling than bounces back to your target before
  hitting your stop. The risk/reward (win 5%, lose 10%) needs a win rate above
  ~67% to break even — we only got ~40%.
- Lesson: **the entry quality (win rate) is the bottleneck, not the parameters.**
  Changing percentages can't fix an entry that wins less than half the time.

## Lesson 3: fees are the silent killer

- The losing 5-minute ladder paid **$15,000+ in fees** on a $100,000 account.
- A strategy can look profitable before fees and lose after them. Always check
  "after fees".
- Regime switches (range → trend) cost a "flatten" taker fee each time; a
  nervous filter bleeds money.

## Lesson 4: it's not "the market is wrong", it's "our plan didn't fit"

The proven-in-literature edges (e.g. e022's two-sided grid, +1.7%..+3.6% over
years) are THIN and fragile: tiny advantages, easily lost to imperfect
execution. Be suspicious of any backtest showing 50%+ returns: either fees are
hidden or the past pattern won't repeat.

## How to read the 4 example pages in this experiment

| File | What it teaches |
|---|---|
| `output/viz_ladder_5m.html` | A losing ladder: thousands of tiny trades, fees eat everything, PF 0.59 |
| `output/viz_ladder_1h.html` | The same idea, wider: barely trades, still PF 0.62 (entry quality) |
| `output/viz_grid_1h.html` | Two-sided grid after the fix: PF 1.00 = split even after fees |
| `output/viz_grid_5m.html` | Two-sided grid on 5-minute data: PF 0.96, still slightly negative |

Open any page: it shows equity, price with buy/sell marks, every trade, the
growing Profit factor, and the glossary.