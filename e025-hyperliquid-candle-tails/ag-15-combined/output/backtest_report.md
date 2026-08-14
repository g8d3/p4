# ag-15 — Combined reversion strategy: crash OR low-volume down

Phase 7 of e025. Pools the two independent reversion findings of the
experiment — **T1** (1d crash, `ret < −3σ`, ag-07/ag-08) and **T2** (1d down
move on unusually low volume for its size, ag-14 signal 5) — into ONE strategy
and backtests it out-of-sample, net of fees, with the same walk-forward
discipline ag-08 established. Everything here was decided before any OOS number
was computed (fixed grid, no tuning — the ag-06 lesson).

---

## Plain English (first, as required)

**What we are testing.** Two earlier phases each found a way to predict that a
coin's price would *bounce back* after falling:

- ag-08: after a **crash** (a one-day drop bigger than 3× the coin's usual
  daily swing) the next 5 days are usually up (+1.24% net per trade).
- ag-14: after a **quiet down day** (a drop that happened on unusually low
  volume for how big the drop was) the next 5 days are usually up (+1.18pp net).

Both sound like the same phenomenon — "an unconfirmed decline reverts". So this
phase asks: are they really the same, and does using *either* signal as a single
strategy give more trades with the same edge?

**What "out-of-sample" means (same rule as ag-08).** For each coin, the 3σ
threshold *and* the "low volume" cutoff are computed **only from the first half**
of that coin's history. Trades are then taken **only in the second half**. The
second half never influenced the rule.

**What we compare (five rules, fixed before results):**
- **A** — buy only after crashes (T1). The ag-08 result, reproduced here.
- **B** — buy only after quiet down days (T2). The ag-14 result as a strategy.
- **C** — the combined strategy: buy after **either** T1 **or** T2.
- **D** — buy only when **both** T1 and T2 fire together (the "purest" version).
- **E** — the baseline: simply be long every day.

**Fees are real.** Taker 0.045% per side (0.09% round trip); maker 0.018%.

**Bottom line in one paragraph.** The combined strategy **C** gives **312 trades
out-of-sample — 11× more than the crash-only strategy A (28) — and it preserves a
positive edge net of fees** (+0.55% per trade, Sharpe 0.44, total +16.3% vs A's
+3.6%). The two signals are **not the same thing**: only 4.2% of T2 triggers are
also T1 crashes, so B is not "C without crashes" — it is mostly *new* trades. But
the volume filter does **not** refine the crash the way we guessed: the
intersection **D** (crash **and** quiet) had **negative** expectancy (−0.54%,
only 20 trades). In fact the crash edge came entirely from crashes that happened
on *normal-to-high* volume (8 trades, +5.7% each, 8/8 wins) — a small-sample
observation, not a new claim. Verdict: **pooling works — bigger sample, edge
survives costs — but "unconfirmed crashes revert strongest" is not supported.**

---

## Rules under test (the fixed grid — not tuned)

| Rule | Trigger | Entry | Hold | Exit | n (OOS) |
|---|---|---|---|---|---|
| **A** | T1 only (crash, `ret < −3σ`) | close of trigger day | 5 d | next close | 28 |
| **B** | T2 only (down ∧ low-volume-for-size) | same | 5 d | same | 308 |
| **C** | **T1 OR T2** (the combined strategy) | same | 5 d | same | 312 |
| **D** | T1 AND T2 (intersection) | same | 5 d | same | 20 |
| **E** | always long (baseline) | buy close | 1 d | next close | 5,123 |

Equal notional per coin, no leverage, **one position per coin at a time** (no
re-entry while a position is open). The trigger candle's own return is **not**
part of the trade — we enter at its close.

**Return definition (exact):** for a trade entered at the close of candle `t`
and held `H` candles, `P&L = (close[t+H] − close[t]) / close[t]`. Fees are
applied multiplicatively at entry and exit:
`net = (1+gross) × (1−fee) × (1−fee) − 1`.

---

## Trigger definitions (exact — re-implemented from ag-08 and ag-14)

**T1 — crash (ag-08).** Per coin, 1d close-to-close return
`ret[t] = (c[t]−c[t−1])/c[t−1]` (v=0 synthetic candles dropped). `σ` = stdev of
`ret` on the **first half** only (ddof=1). `T1` iff `ret[t] < −3σ`. This
reproduces ag-08 exactly (same 28 trades, same +1.24% net, same 8 crash days).

**T2 — low-volume down (ag-14, signal 5).** Per coin:
`median_v[t]` = causal trailing rolling median of `v` over the last 101 candles
(min 30) — the walk-forward analog of ag-14's full-series median. ag-14 used the
whole series median; we had to move it to a causal estimate, and a *static
first-half* median is a terrible baseline here because volumes grew 10–20× over
the sample (BTC 1.4k→29k per candle), which would make second-half |vol_adj|
tiny and T2 never fire. The 101-window is the same window ag-14 used for its
causal volume percentile. **Stated choice.**

`rel_vol[t] = v[t] / median_v[t]`, `vol_adj[t] = ret[t] / rel_vol[t]` (ret in %,
exactly ag-14's `sr / rel_vol`). The quintile is of `|vol_adj|` **within down
moves** (ag-14's report describes the bucket as "quintiles of |vol_adj| per
(coin,tf) within each sign"; its code pooled signs but with ~50/50 up/down
splits the two cutoffs coincide — stated choice). `q5` = 80th percentile of
`|vol_adj|` over **first-half down moves**. `T2` iff `ret[t] < 0` **and**
`|vol_adj[t]| ≥ q5`.

Calibration check: 19.8% of second-half down moves are flagged T2 — right at the
20% a quintile should give, confirming the rolling baseline keeps scales
comparable.

Both thresholds come **only** from the first half; triggers are detected and
traded on the **second half only**.

---

## Out-of-sample window

- Per coin, OOS = second half by time of its real 1d series (v>0 candles only).
- Pooled window: **2024-11-19 → 2026-08-13** (per-coin OOS starts range
  2024-11-19 for BTC/ETH up to 2026-04-30 for XMR; all end 2026-08-13).
- Trade counts: **A = 28, B = 308, C = 312, D = 20, E = 5,123**.
- Distinct entry days: A = **8**, B = **154**, C = **155**, D = 8. The combined
  strategy trades on ~155 different calendar days instead of A's 8 — the sample
  is not just bigger, it is far more *independent*.

---

## Results — metrics table

Portfolio metrics are on the **market-pooled** series (ag-08 convention): each
calendar day, the equal-weight mean return across the coins alive that day; a
coin with no position contributes 0.

### Portfolio metrics (gross AND net of fees)

| Rule | Total gross | Total net (taker) | Total net (maker) | Expectancy net (taker) | Win rate net | Max DD net | Sharpe (taker) |
|---|---|---|---|---|---|---|---|
| **A — crash only** | +3.91% | **+3.58%** | +3.78% | **+1.24%** | **67.9%** | −9.03% | 0.22 |
| **B — low-vol down only** | +17.52% | **+13.49%** | +15.89% | **+0.48%** | 48.1% | −32.50% | 0.39 |
| **C — T1 OR T2 (combined)** | +20.49% | **+16.31%** | +18.80% | **+0.55%** | 48.7% | −32.35% | **0.44** |
| D — T1 AND T2 (intersection) | −1.17% | −1.40% | −1.26% | −0.54% | 55.0% | −8.02% | −0.05 |
| E — always long (baseline) | −42.22% | −67.24% | −53.95% | −0.10% | 46.6% | −75.62% | −0.59 |

Definitions: **Total return** = compounded pooled return over the OOS window.
**Expectancy** = mean P&L per trade (net). **Win rate** = fraction of trades
with positive P&L (net). **Max drawdown** = worst peak-to-trough decline of the
pooled equity (net). **Sharpe-style** = mean ÷ std of daily pooled returns ×
√365 (annualized; NOT a true trade Sharpe).

### Trade-level metrics

| Rule | n | Mean gross | Mean net taker | Mean net maker | Win gross | Win net taker |
|---|---|---|---|---|---|---|
| A — crash | 28 | +1.33% | +1.24% | +1.29% | 71.4% | 67.9% |
| B — low-vol down | 308 | +0.57% | +0.48% | +0.54% | 48.4% | 48.1% |
| C — combined | 312 | +0.64% | +0.55% | +0.61% | 49.0% | 48.7% |
| D — intersection | 20 | −0.45% | −0.54% | −0.48% | 60.0% | 55.0% |
| E — baseline | 5,123 | −0.010% | −0.100% | −0.046% | 47.8% | 46.6% |

**A reproduction check:** Rule A here matches ag-08's numbers exactly (28 trades,
+1.24% net, 67.9% win, +3.58% total, −9.03% DD, Sharpe 0.22) and Rule E matches
ag-08's Rule C baseline (−67.24%, −75.62% DD). The machinery is the same one.

---

## The four answers

### 1. Sample gain — C gives 11× the trades, edge preserved in sign (weaker per trade)

- **C = 312 trades vs A = 28: +284 trades (11.1×)**, spread over 155 distinct
  days vs A's 8. This is the core win: the combined signal's numbers are far
  more trustworthy than the crash-only sample, which collapsed to ~8 shared
  market-wide crash days.
- **Edge at the larger sample:** C's net expectancy is **+0.55%** (still ~6× the
  0.09% round trip) and its Sharpe (0.44) is *twice* A's (0.22). Total return
  roughly quadruples (+16.3% vs +3.6%). Win rate falls from 68% (A) to 49% (C)
  because B carries a thin right tail (median B trade is −0.24%, p90 +11.3%,
  a few +25–33% winners) — a classic mean-reversion profile, not a coin-flip.
- Net-of-fees expectancy stays positive at **n=312 ≫ 50**, the pre-declared
  credibility threshold. The thesis gains real credibility on sample size.

### 2. Does volume refine the crash? — No: the intersection is small AND negative

- **D (crash ∧ low-volume) = 20 trades, −0.54% net.** Not above the pre-declared
  n≥30 bar, and its sign is *negative*, so **"unconfirmed crashes revert
  strongest" is NOT supported.** The purest intersection did not make money.
- Decomposing A: the **8 crashes that were NOT low-volume-for-size** (i.e.
  crashes on relatively *normal/high* volume — T1-only) had **+5.68% net per
  trade, 8/8 wins** (2026-02-05 alone contributed 5 of them). The 20 quiet
  crashes (T1+T2) lost money. So if anything the data points the *opposite* way:
  loud, volume-backed crashes reverted; quiet ones drifted.
- **Caveat:** this decomposition is *post-hoc observation*, not a declared rule —
  we did not (and must not, per the fixed-grid rule) convert "T1 ∧ NOT T2" into a
  new strategy on the strength of 8 trades. Report it as a lead for a future
  phase, nothing more.

### 3. Is T2 independent of T1? — Largely yes (only 4.2% of T2 are also T1)

- Second half: **30 T1 triggers, 530 T2 triggers, 22 in both.**
  - **4.2%** of T2 triggers are also T1 → B is NOT "C without crashes"; ~96% of
    B's trades are new, non-crash entries.
  - **73%** of T1 triggers are also T2 → most crashes also qualify as low-volume
    down moves (a big move on "enough" volume is still large in |vol_adj| terms),
    but crashes are rare, so they barely touch T2's population.
- Verdict: the two analyses are **mostly different phenomena** with a small
  overlap in the crash direction. Pooling them is legitimate sample
  enlargement, not double-counting the same trades (per `output/trigger_overlap.csv`).

### 4. Net-of-fees metrics for every rule — table above, highlights

- Only **A and C beat the baseline E**; **B also beats E** on total return
  (+13.5% vs −67.2%) but with a deep −32.5% DD — the low-volume signal is
  positive but carries crash risk (its worst losses cluster on 2025-02-01 and
  2026-01-29/31, the same market-wide crash days that hurt everything).
- **C dominates B** (better expectancy +0.55 vs +0.48, better Sharpe 0.44 vs
  0.39, only 2 extra trades lost to the single-position rule) and **dominates A**
  (11× sample, 2× Sharpe, ~4.5× total return). C is the best all-round rule.

---

## Per-coin results (net of taker fees)

| Coin | A n | A mean | B n | B mean | C n | C mean | D n | D mean |
|---|---|---|---|---|---|---|---|---|
| BTC | 2 | +4.63% | 32 | −0.39% | 32 | −0.39% | 2 | +4.63% |
| ETH | 6 | −4.90% | 50 | −0.18% | 50 | −0.18% | 6 | −4.90% |
| HYPE | 0 | — | 19 | +2.54% | 19 | +2.54% | 0 | — |
| SOL | 4 | +1.59% | 32 | −1.53% | 33 | −1.38% | 2 | −0.28% |
| PUMP | 0 | — | 3 | +4.75% | 3 | +4.75% | 0 | — |
| ZEC | 0 | — | 1 | −3.32% | 1 | −3.32% | 0 | — |
| XRP | 3 | +4.79% | 53 | +0.65% | 54 | +0.92% | 2 | −0.40% |
| LIT | 0 | — | 5 | +6.89% | 5 | +6.89% | 0 | — |
| DOGE | 3 | +0.84% | 34 | −0.70% | 35 | −0.56% | 1 | −3.58% |
| CRV | 4 | +0.39% | 37 | +1.16% | 37 | +0.99% | 3 | +0.22% |
| AAVE | 5 | +4.37% | 41 | +1.43% | 41 | +1.43% | 4 | +3.40% |
| XMR | 1 | +8.09% | 1 | +12.5% | 2 | +10.3% | 0 | — |

- A: 7/8 coins that traded positive (the ag-08 result, unchanged).
- B: 6/12 coins positive, 7/12 for C. The pooled edge comes from a mix of
  big winners (AAVE, CRV, LIT, HYPE, XMR) and a drag from BTC/ETH/SOL/DOGE.

---

## Honest caveats that cap the conclusion

1. **B/C's win rate is below 50%.** The positive expectancy is a right-tail
   story (median trade negative). Mean-reversion systems live and die on
   letting winners run; the −32% pooled drawdown is real.
2. **The crash decomposition (answer 2) is 8 trades.** "Loud crashes revert,
   quiet ones don't" is a *lead*, not a finding.
3. **Correlated coins.** B/C trade ~155 days but the 12 coins move together;
   the effective independent sample is smaller than 312.
4. **One regime.** The OOS window is one bear regime; nothing here speaks to
   behavior in a bull market.
5. **The q5 baseline was adapted** from ag-14's full-series median to a causal
   rolling median (stated in the definitions) — necessary for honest OOS, but
   not byte-for-byte ag-14's code.

---

## Files produced

| File | Contents |
|---|---|
| `output/backtest.csv` | One row per (coin, rule, trade): entry/exit, gross + net P&L, fees, trigger (T1/T2/T1+T2) |
| `output/backtest_report.md` | this report |
| `output/equity.png` | Equity curves A/B/C/D/E net of taker fees (pooled, log scale) |
| `output/trigger_overlap.csv` | Per-coin T1∩T2 overlap stats |
| `output/oos_windows.csv` | Per-coin OOS window, σ, median_v, q5 threshold |
| `output/per_coin.csv` | Per-coin summary for every rule |
| `output/equity_daily.csv` | Daily pooled equity index per rule |
| `output/metrics.json` | Machine-readable metrics |
| `output/beginners_guide.md` | This pipeline explained for a beginner |
| `output/session-log.md` | Declared grid + what was done |

---

## Verdict

> **Pooling the two reversion triggers works: the combined strategy's edge
> survives out-of-sample net of fees on an 11× larger, far more independent
> sample (312 trades, +0.55%/trade net, Sharpe 0.44) — the credible win.**
>
> But the volume filter does **not** refine the crash signal. The "purest"
> intersection D (crash ∧ low-volume) had negative expectancy (−0.54%, 20
> trades); the crash edge actually sat in the 8 high-volume crashes (+5.7% each,
> 8/8 wins) — a small-sample lead, not a rule. And T2 is **not** the same
> phenomenon as T1: only 4.2% of T2 triggers are crashes, so B adds genuinely
> new trades rather than duplicating A.
>
> The honest bottom line: mean-reversion of declines survives — more credibly
> than before, because the sample is 11× larger — but the "quiet, unconfirmed
> decline reverts strongest" refinement is contradicted by the intersection.
> Statistical exercise on history, not investment advice.
