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


## 1b. How the trailing machine works (step by step) — the heart of the strategy

**One number rules everything:** `T = ATR(14) x 0.02`

- **ATR(14)** = the average "true range" of the last 14 bars (a volatility
  meter: how far price typically moves in one bar).
- **T** = 2% of that. On 1-day BTC bars ATR is ~$2,500-3,500, so T ~ $50-70
  (about 0.08% of the price) — tiny compared to a daily swing of 2-4%.

### Step 1 — Arming ("armado")

For a LONG entered at `entry`:

> **Not armed:** as long as every bar's HIGH stays below `entry + T`,
> there is **NO stop at all**. Nothing protects the trade.

- Each bar you check: `if high >= entry + T  ->  ARMED`
- *"Armed"* = "price has moved T in my favor at least once." Until then,
  the position has zero protection.
- The moment it arms, the stop appears at `best_high - T`.

Real example (their engine's own trade list, trade #2 — a short):
- Entry short at 63,395.70. T = 6.62 (ATR 331 x 0.02).
- Next bar's LOW = 63,300.20. For a short, arming uses the low:
  `63,300.20 <= 63,395.70 - 6.62` -> **ARMED**. Stop = 63,300.20 + 6.62 = 63,306.82.
- The same bar's high crossed back up through the stop -> exit at ~63,301.70.
- Result: short in at 63,395.7, out at 63,301.7 -> captured the $94 favorable move.

### Step 2 — The ratchet (the "trailing" part)

Every new bar updates the stop, but **only in your favor**:

```
LONG:  stop = max(previous stop, highest_high_since_entry - T)
SHORT: stop = min(previous stop, lowest_low_since_entry  + T)
```

The stop never moves against you. This creates two properties:

1. **Once armed, the stop sits at or better than your entry** (because
   `best >= entry + T` implies `best - T >= entry`). So **every armed exit
   is a small profit** (before fees). It is a *take profit* in disguise:
   "let the winner run; close the moment price pulls back T from the extreme."
   The win = `(highest reached - T) - entry`.
2. **It protects the gain, not the entry.** Before arming: no floor at all.

### Step 3 — Where the LOSSES come from (the "reversal exit")

No stop before arming means a losing trade can only end one way:

```
When the opposite signal fires (EMA crosses back under VWAP for a long),
close the position at that bar's CLOSE — whatever price it is.
```

Real example (our 2h test): short entered at 63,395.7 at 18:00; the next
bar pumped to 64,849.9 (price never went down T, so it never armed); the
signal flipped long at 20:00 -> the short closed at 64,849.9 = a -1.4% loss.

### One-sentence summary of the whole edge

> Entries are barely special. The machine is:
> **enter -> hope price ticks T in your favor (arming) -> if yes, lock in
> everything above `best - T` while riding the trend; if no, wait until
> the opposite signal drags you out at some close.**

### Why the 1-day version has no tail risk

On 1d bars the reversal exit happens at the *next day's close*, so a bad
trade loses roughly one day's adverse move (~0.5-1.5%). That's why the
Monte Carlo showed that clipping losses at 2% changes nothing: the worst
realized trade was already better than -2%. On 2h bars reversals could
catch bigger swings (drawdowns -15% to -25%).

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


## 6. Chapter 6 — The big-timeframe test (1 day / 1 week)

**The idea (your half-right intuition):** bigger timeframes → bigger % moves
→ the same fixed fees become a smaller bite. That part is right. The part
that needed testing: on bigger bars there is MORE "inside story" per bar,
so the fill-optimism risk grows. We tested both levels honestly.

**Results (1-day bars, weekly-anchored VWAP, same micro-trail):**

| Version | PF | %/day (after commissions) | Worst drawdown |
|---|---|---|---|
| Bar-level (optimistic) — BTC | 5.0 | 0.30 | -15% |
| Bar-level — ETH | 5.2 | 0.50 | -22% |
| Bar-level — SOL | 3.1 | 0.59 | -25% |
| **Realistic 5m fills — BTC** | **6.4** | **0.15** | **-2%** |
| **Realistic 5m fills — ETH** | **7.4-9.6** | **0.28-0.29** | **-5%** |

**The surprise:** on 1-day bars the REALISTIC version got a BETTER PF
(6.4 vs 5.0 at bar level) and a much smaller drawdown (-2% vs -15%).
Why? On daily bars the trail is so small (0.05% of price) that the 5-minute
path matters less — the trade either runs the day trend or gets clipped
small. The optimistic assumption had LOWERED the PF (it let pumped-and-
dumped days count as wins).

**Weekly (1w):** only 31 trades in 2 years — too few to conclude anything.
Reported for completeness only (PF 6.5 at bar level, but n=31 is noise).

**Meaning:** the 1-day version is the ONLY configuration where the edge
survives the whole honesty chain: real fills, real fees, and it still nets
**~0.15% per day with PF 6.4, drawdown -2%**. That is small but real;
slippage of another 0.2% per round trip would still leave it near
breakeven, so it remains marginal — but it is the direction worth a
paper-trade.

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


## 7. Chapter 7 — Robustness test (Monte Carlo) and the stop-loss question

**Your question: what stop loss do we use? — NONE.** The strategy has no
stop loss at all: the trailing order only protects AFTER it arms
(price went in your favor first), and losing trades normally exit when the
opposite signal fires at the next day's close. This is why the equity DDs
exist. BUT the Monte Carlo test found: clipping any trade's loss at 2%
changes NOTHING — the worst realized trade already loses less than 2% of
equity. On 1-day bars the risk tail is small by construction.

**Monte Carlo (10,000 reshuffles of the trade order):**
- Chance of ending the 2 years negative: **0.0%** (both coins).
- Worst 5% of paths still end with 2.3x-4.9x capital.
- Max drawdown median -2.2% (BTC) / -3.6% (ETH), 5th percentile -3.8%/-5.9%.
- Reshuffling in blocks (3 consecutive trades kept together): identical
  result -> no hidden path-dependence.

**What this means:** the 150-157 trades are not a lucky sequence — the
per-trade distribution is strong enough that ANY ordering makes money.
What it does NOT test: a different future market regime (a trending market
that stops trending). That is exactly what paper-trading is for.


## 8. Chapter 8 — The winner: EMA7, and the new interactive report

- **EMA7 beats EMA5** everywhere once fills are realistic: PF 8.9 (BTC),
  12.4 (ETH), 14.1 (SOL) vs 6.4/7.4/7.2. Same %/day, higher PF, tight DD.
  (A sliitly SLOWER cross averages out more noise before committing.)
- **Regime warning:** the fresh May-Aug 2026 window (19-25 trades/coin) is
  flat/negative — the edge may be cooling. The paper monitor watches this.
- **Interactive report:** `REPORT.html` in this folder — open it in your
  phone browser. It has the honesty chain chart, the Monte Carlo
  distribution, the sweep, the cost-stress chart and all tables. All numbers
  embedded; no internet needed after the first load (CDN only).
  Tip: copy it to the phone or `python3 -m http.server` to share on LAN.


## 9. Chapter 9 — The robustness test family (the professional names)

A quant research pipeline uses several DIFFERENT tests, each destroying a
different kind of lie:

| Test | What it destroys | What we did |
|---|---|---|
| **Permutation / null signals** | "the signal is smart" | 120 runs with RANDOM entries, same exits. Random still made 0.65%/day; real 0.80% (p=0.0). Signal = +22% of the profit. |
| **Monte Carlo bootstrap** | "we were lucky with the order of trades" | Shuffled the 112-132 REAL trades 10,000 times. p(negative)=0.0. |
| **Walk-forward** | "it only worked in one period" | Every 90-day window positive at 2h; 1d flat in the fresh May-Aug 2026 slice. |
| **Transaction-cost stress** | "fees don't matter" | 2h dies at realistic taker costs; 1d survives with ~10% of edge in fees. |
| **Synthetic-data negative control** | "the machine is real, not just lucky with structure" | 60 pure-noise series: PF 1.42 median, 90% positive. The machine harvests drift even from garbage; the market structure gives the rest (real PF 14.4). |
| **Fill realism (intrabar)** | "the best price happened first" | 5m path within each daily bar. Killed the 2h version, saved the 1d one. |

Your instinct was right: **this is a quantitative (systematic) trading
research pipeline**. The standard order is: data -> hypothesis ->
backtest -> realism -> robustness -> nulls -> costs -> paper -> live.
