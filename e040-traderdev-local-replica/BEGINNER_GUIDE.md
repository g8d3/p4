# e040 — The investigation explained from scratch

*A beginner-friendly walkthrough of what was done, why, and what it means.
Written for someone who has never backtested anything.*

---

## 0. The whole thing in one sentence

**We took the "winning strategy" of a website, tested it ourselves on the
real market data we downloaded, and discovered that its impressive numbers
come from optimistic assumptions (not from real money-making).**

---

## 1. The vocabulary, with analogies

| Term | What it means | Analogy |
|---|---|---|
| **Signal** | The rule that says "buy" or "sell" | The sound of the rope being pulled to start a race |
| **Entry / Exit** | When you open / close a position | Opening / closing your store |
| **Trailing stop** | A protective order that FOLLOWS the price as it goes up, keeping a small distance behind it | A guard dog walking behind you: if you stop, it bites and you get out |
| **Micro-trail** | A trailing stop set very, very close to the price (small distance) | A guard dog on a very short leash |
| **Bar (candle)** | One chunk of time, with the highest and lowest price reached in it | 1 page of the price diary (each page = 2 hours, for example) |
| **Backtest** | A computer program that replays the past and asks: "if I had followed these rules, what would I have made?" | Rewinding a football match and betting on it for real, to see who would win |
| **PF (profit factor)** | Total money won ÷ total money lost | If you win 5 bets and lose 1, PF = 5. PF > 1 = profitable; PF 14 looks amazing |
| **Drawdown** | The worst drop your money suffers along the way | The deepest valley on the way up the mountain |
| **Win rate** | % of trades that end positive | How many of your predictions are right |
| **Commission** | Fee the exchange charges per trade (in crypto: ~0.05% per side) | The casino's cut on every bet |
| **Slippage** | You ask for price X but the market moved and you actually get X+0.1% | Paying more at the store than the price tag said |
| **Taker** | You buy at the current price (pay fee, fast) | Jumping the line (you pay more) |
| **Maker** | You POST a price and wait for someone to fill you (receive discount) | Standing politely in line (you pay less) |
| **Permutation test** | Randomize the "buy/sell signals" (throw darts instead of following the rule) and see if random dart throws make the same money | Is the chef good, or is the recipe so simple that anyone could cook it? |
| **p = 0.0** | The probability that random signals would beat the real ones by luck = 0%. It means the signal DOES help... | The chef is better than a monkey at the kitchen — we're sure |
| **Walk-forward** | Split time into chunks, test each chunk separately | Don't judge a whole year; check season by season |
| **Intrabar / realistic fills** | Simulating the actual price path WITHIN each 2-hour page using 1-minute data | Watching the minute-by-minute footage instead of only reading the page summary |
| **Bar-optimism** | The simulator assumes the GOOD price happened first inside the bar | Believing the traffic light was green exactly when you arrived |

---

## 2. The story, chapter by chapter

### Chapter 1 — We found a "top strategy" advertised on the website

Trader.dev displays public strategies ranked by results. The #1 pattern is
absurdly simple: when the EMA (a fast moving average) crosses the VWAP
(an average price weighted by volume), buy. Then use a trailing stop set at
an absurdly small distance (a tiny fraction of ATR, the volatility measure).

Published result: **+16,000% in 2 years, PF 14** — numbers that would make
anyone rich if they were real.

### Chapter 2 — We checked what their engine actually does (1 credit)

We ran ONE test on THEIR machine and downloaded the exact list of trades.
Two discoveries:

1. The position size is NOT 10x (we first assumed that). It is 1x equity.
2. Their engine has a quirk: on a few trades, it fires the "long exit"
   order and the "short exit" order at the same time, capping losses
   (*accidentally beneficial* — like their guard dog accidentally catching
   a fruit from a tree). **Real TradingView would NOT do this.**

Those two details already explain a large part of their gorgeous numbers.

### Chapter 3 — We built our own honest simulator and validated it

We recreated the strategy in pandas (a Python library for tables) using
PUBLIC market data (Bybit exchange klines — free, no API key).

At first we made three mistakes in our own simulator (used 10x leverage,
checked the wrong bar for short entries, and mispriced the stop fills).
Each mistake taught us something about the strategy. After fixing them, our
simulator matched their engine trade-for-trade on the clean cases
(entry at 64186.1, exit at 64238.55, etc.).

Running the same window as them, we reproduced the same phenomenon:
**+22,000% net, PF 6.5-18, win rate 81-84%, drawdown 2-6%.** Same family of
results.

### Chapter 4 — The questions that ruin the party

Then we attacked our own result as if we wanted to destroy it:

**Q1: Is the SIGNAL special, or is the EXIT (trailing stop) doing all the work?**
*Permutation test*: we threw random darts (random signals, same number of
buys/sells) and ran them through the same exit logic. Result: random darts
made **0.65% per day**; the real signal made **0.80% per day**. So:
- The random version (p = 0.0) almost reached the real one: **about 80% of
  the profit comes from the trailing stop itself, not from the signal.**
- BUT p = 0.0 also means the real signal IS better than every single one of
  120 random darts — so the signal helps a little (+22% of the profit),
  it's just not the star.

**Q2: Does precise timing matter?**
*Time-shift test*: we delayed every entry by 1, 2, 3 bars (4-6 hours later).
Nothing changed (0.73-0.82%/day). The edge doesn't need precise timing.
→ This is another clue that it's not a "smart signal" edge; it's a
"structure" edge (any entry riding a small trailing stop during mild trends).

**Q3: Is one direction better?**
We tested buys-only and sells-only. No: the winning leg rotates. Sometimes
shorts win (SOL in the last months), sometimes longs. Your intuition is
right — the strategy works both ways.

**Q4: What if prices move against us quickly?**
*Walk-forward*: we cut time into 8 windows of 90 days each. EVERY window
was profitable (0.46-1.09%/day). The edge is stable over time — the
previous suspicion "this only worked in one lucky regime" is rejected.

**Q5: What happens with REAL costs?**
*Fee/slippage stress*: starting from the realistic benchmark
(0.05% commission):
- + 0 % slippage → 0.26%/day (PF 5.8)
- + 0.1 % slippage → 0.12%/day (PF 2.2)
- + 0.3 % slippage → **−0.17%/day (LOSES money)**

At 0.1% commission + 0.1% slippage (what a normal taker pays on crypto)
the strategy earns 0.04%/day — basically nothing.

**Q6: Are our fills even possible in real life?**
Our simulator assumed: *in each 2-hour bar, the good price happened first*.
That is the "bar-optimism" trap — and where it bites: we downloaded
225,000 one-minute candles and re-simulated the EXACT same strategy, but
now following the real 1-minute sequence inside every 2-hour bar.

Result: **PF 1.36-1.58, 0.11-0.20% per day.** About 70% of the "profit"
was fiction created by the assumption. What remains (0.1-0.2%/day) is
eaten by real costs ≈ zero result.

*(We tried the same realistic test with the ZScore variant — a different
signal family — and it LOST money (PF 0.53). No variant survives.)*

---

## 3. Your three questions, answered directly

1. **"¿No es la señal la que da ganancias, sino el trailing take profit?"**
   → EXACTLY RIGHT. The trailing stop machine does ~80% of the work. The
   signal only adds ~22% on top.

2. **"¿Funciona tanto para short como para long?"**
   → YES. Both directions work; which one contributes more rotates with
   the market period.

3. **"¿Entonces la solución es usar timeframes más grandes?"**
   → Partly, but the true reason isn't "bigger bars" per se — it's that on
   bigger timeframes each trade captures a LARGER percentage move, so the
   SAME fixed fees become a smaller share of each win (the fees stay ~0.1%
   but the win goes from ~0.2% to ~1-2%). SECONDARY benefit: fewer trades
   (fewer fee total), and the bar-optimism effect is smaller relative to
   the move. So the idea remains CANONICAL: the concept might survive at
   1D/1W where costs stop mattering. We just haven't tested it yet.

---

## 4. What this means practically

- The website's +16,000%: **not real money**. It's a chain of optimistic
  assumptions (their engine quirks + bar-optimism).
- Would you lose money trading it live as a taker? Very likely ~breakeven
  or slightly negative, because you pay the realistic fees we simulated.
- What remains honest and valuable:
  1. The METHODOLOGY you now have (how to test ANY strategy honestly).
  2. The finding that micro-trail exits mine "market drift" — interesting
     physics, but it only pays if costs are near zero (Maker on
     Hyperliquid, or big timeframes).
  3. Candidates for a future test: the same pattern at 1D/1W, or maker-only
     simulation.

## 5. Where each proof lives (files)

| File | What it is |
|---|---|
| `output/FINAL_REPORT.md` | The technical report (what you read) |
| `output/falsification.json` | The dart-throwing + stress numbers |
| `output/intrabar.json` | The honest-fill test |
| `bin/backtest.py` | Our honest simulator (the tool you can reuse) |

*Made in e040-traderdev-local-replica, 2026-08-22.*
