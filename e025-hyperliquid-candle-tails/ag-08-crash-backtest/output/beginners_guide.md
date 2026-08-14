# Beginners guide — backtesting "buy the crash" honestly

This guide explains, in plain language, every idea used in the ag-08 backtest.
You do not need any background in finance or statistics. By the end you will
know: what a backtest is, why "out-of-sample" matters so much, what
expectancy, drawdown, Sharpe ratio and fees are, and — the most important
lesson — why this experiment's answer is deliberately *weak*.

---

## 1. What is a backtest?

A backtest is a **replay of history**. We have a giant spreadsheet of every
coin's daily price. We pretend it is still today, and we "run" a rule over the
old prices to see how much money the rule would have made.

The rule we tested here is called **buy the crash**:

> If a coin drops more than 3σ in one day (a "crash"), buy it at that day's
> close and hold it for 5 days.

σ (sigma, "sigma") is a measure of how much a coin normally swings. Three
sigma means "a swing three times bigger than normal" — a genuinely rare,
scary day. (σ is computed separately for each coin, because BTC swings less
than a small altcoin.)

We also test two **control** rules, because a single rule proves nothing:

- **Buy the rally** — same idea, but buy after a *big up* day instead of a big
  down day.
- **Always long** — just own the coin every single day.

Why controls? Imagine you test "buy the crash" and it makes money. Is that
because crashes bounce, or because *anything* you buy goes up? If buying the
rally also made money, the effect is not about crashes at all. The controls
tell you whether your result is *specific* to your idea.

---

## 2. The single most important idea: out-of-sample (OOS)

This is the heart of the whole experiment, and the easiest thing to get wrong.

**The trap.** If you look at a whole history of prices, you will find
"patterns". Your brain (or a computer) can always find *some* rule that would
have made money — even if the rule is actually nonsense. This is called
**curve-fitting** or **overfitting**. The rule is "fit" to the exact history,
like a tailor making a suit that only fits one specific person.

**The fix.** Split each coin's history in two by time:

- **First half** — used to *design* the rule. Here we compute σ.
- **Second half** — never touched while designing. Here we run the trade.

The second half is "out of sample": the rule has never "seen" it. If the rule
works there too, it is much more likely the pattern is real and not just a
perfect fit to old noise.

Think of it like a teacher. If a teacher writes a test and then takes it
themselves, of course they pass. The honest test is a *new* student taking a
*new* exam.

---

## 3. How fees change everything

Exchanges charge you money every time you trade. This is the **fee**:

- **Taker fee**: you pay to grab liquidity instantly — 0.045% of the trade on
  each side. Buying and selling = 0.09% total.
- **Maker fee**: you get paid to provide liquidity to the order book — 0.018%
  each side (cheaper).

So if you buy a coin and it goes up 0.05% in a day, you actually *lost* money
after paying to enter and exit. Fees are small per trade but they pile up
fast. In this backtest, "always long" pays a fee *every single day* — that is
a big part of why it lost so much. We always show results **gross** (no fees,
the fantasy world) and **net** (real world, after fees). The honest number is
the net one.

---

## 4. The metrics, one by one

- **Total return** — if I start with $100 and follow the rule over the whole
  window, what do I end with? +3.58% means $103.58.
- **Expectancy** — the *average* profit per trade. +1.24% means "on average,
  each crash-buy made 1.24%". This is the single most useful number: it says
  what one trade is worth on average.
- **Win rate** — what fraction of trades made money? 68% means "about 2 of
  every 3 crash-buys were profitable".
- **Max drawdown** — the worst point. If at some moment you were down 9% from
  your best point, that is a 9% drawdown. It tells you how much pain you must
  be able to stomach. A strategy can make money in the end and still dip
  badly in the middle.
- **Sharpe-style ratio** — "how much reward per unit of wobble". It compares
  average daily gains to how jumpy the daily gains are. Higher = smoother
  profit. Below ~1 is not exciting. Ours (0.22 for Rule A) is low — the
  strategy makes money but rarely, with the equity curve mostly flat.

---

## 5. Why the answer here is deliberately weak (read this twice)

The whole point of this experiment is **honesty over excitement**. Here is
what the numbers actually say:

| Rule | Average profit per trade (net) | Win rate |
|---|---|---|
| Buy the crash (the idea) | **+1.24%** | 68% |
| Buy the rally (control) | −4.81% | 18% |
| Always long (baseline) | −0.10% | 47% |

Rule A made money. Rule B lost money. The controls did exactly what the idea
predicted: the effect is *specific to crashes*, and it beat just holding the
coin. That is a genuinely encouraging result for the theory.

**But** — and this is the lesson — there were only **28 crash trades**, which
is **fewer than the 30 we promised we needed**, and because all 12 coins move
together, those 28 trades are really only **about 8 separate market-wide crash
days**. Statistically, 8 or 28 observations is a *tiny* sample. The average
"+1.24%" could easily be a different number (even a negative one) if we had a
bit more history. And the whole window was a bear market — we have no idea how
the rule behaves in a bull market.

So the verdict is deliberately cautious:

> **This looks real, but it is not proven. It is directional evidence.**

That caution is the correct scientific answer, and it is the point of the
whole experiment: a backtest measures, it does not sell you a miracle.

---

## 6. Risk caveat (plain words)

This is a statistical exercise on historical prices. It is **not trading
advice**, and past results do not predict the future. Even a "real" edge can
fail tomorrow, and trading involves the risk of losing real money. Think of
this project as a lab experiment — learning how to test ideas honestly — not
as a way to get rich.

---

## 7. How this fits the bigger experiment

- **ag-07** found the pattern (crashes bounce over 5 days) on all the data.
- **ag-08** (this file) re-tested it on the half of the data the pattern never
  saw, with fees and controls. Result: it survives, but weakly.
- Future phases will ask harder questions: does the effect depend on funding
  rates, on how other coins did that day, on how volatile the market was?
  Every phase uses the same discipline: declare the test first, run it on
  data the rule has never seen, report the honest answer.
