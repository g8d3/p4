# ag-12 — Regime drift: are the patterns stable over time?

Date: 2026-08-14
Input: `../ag-01-data/output/candles_raw.csv` (12 coins × 4 tfs; the 3,175
`v=0` synthetic pre-listing candles dropped, as in ag-07 → 132,057 rows).
Questions asked: **is the data stationary?** and **which findings survive a
quarter-by-quarter split?**

Method: each `(coin, tf)` series is cut into **calendar quarters** (2023Q1 →
2026Q3; 2026Q3 is partial, Jul 1–Aug 13). Per `(coin, tf, quarter)` we compute
volatility (σ of close-to-close `ret`, median `range`), tail shape (kurtosis,
p99.9), and 3σ-event frequency (σ = the coin's global, whole-series σ, exactly
as ag-07 defined events). Pattern stability uses two ag-06/ag-07 definitions:
the weekday effect as **same-day intraday** `(c−o)/o` per weekday, and
**daily-crash reversion** as the 5-day close-to-close return after 1d down
3σ events. Trend tests: Kendall τ and log-linear slope of pooled-median σ vs
quarter index.

**Timeframe caveats** (from ag-01, unchanged): 5m only spans ~17.5 days
(one window, not splittable); 1h spans ~7 months (3 partial quarters); 1w has
~13 candles/quarter (thin — treat any 1w per-quarter number as illustrative
only). Only the **1d** series is long enough for a proper drift test.

---

## 1. Volatility level — **NOT stationary. Regime cycles, no monotonic trend.**

Pooled median of daily-return σ per quarter (7 coins with ≥3y history:
BTC/ETH/SOL/AAVE/CRV/DOGE/XRP; full 12-coin pooled in `quarters.csv`):

| Period | σ (median %) | reading |
|---|---|---|
| 2023Q1–Q4 | 2.6 – 3.6 | quiet first year |
| 2024Q1–Q4 | 4.2 – 6.3 | elevated; **2024Q4 = 6.2** peak |
| 2025Q1–Q4 | 3.9 – 5.8 | elevated, drifting down |
| 2026Q1–Q3 | 2.0 – 4.3 | cooling; **2026Q2/Q3 back to 2023 levels** |

- Range: σ nearly **triples** from 2.0% (2026Q3) to 6.2% (2024Q4).
- But the drift is **not a monotonic trend**: 1d Kendall τ = 0.20, p = 0.33,
  log-slope +1.9%/quarter (not significant). It is a **regime cycle** — low in
  2023, high in 2024/early-2025, low again in 2026 — not a steady rise or fall.
- Median intra-candle `range` follows σ (not shown in charts; in `quarters.csv`).
- 1w σ (median over coins) mirrors 1d: 6–11% in 2023–2025 with a 2024Q4 spike
  to 18%, back to ~5% in 2026Q3. Too thin for a reliable trend test (τ 0.05).
- 1h (3 quarters, 2026Q1–Q3): σ 0.60–0.90%, falling to 0.60% in Q3 — one
  regime only, no test possible.
- 5m: single ~17-day window, σ 0.167%. No split possible.

**Verdict: volatility clearly drifts, but it mean-reverts around a range
rather than trending one way. Any strategy sized on a fixed vol level will be
wrong in half of the quarters.**

## 2. Tail shape — **STABLE. Fat tails persist in every single quarter.**

Kurtosis (excess + 3, pooled median) per quarter, 1d:

| Stat | 1d values | reading |
|---|---|---|
| kurtosis range | 3.4 – 9.5 | **always > 3 (fat-tailed)** |
| quarters with kurtosis > 3 | 15 / 15 | 100% |
| 1w kurtosis | 2.5 – 4.9 | thin data, mostly > 3 |
| 1h kurtosis | 6.9 – 10.7 | fat-tailed (one regime) |
| 5m kurtosis | 9.2 | fat-tailed (one window) |

- Tail shape does **not** go away when volatility falls: 2026Q2–Q3 have the
  lowest σ *and* kurtosis still ≈ 3.6–4.3. The fat tails are structural, not a
  by-product of a single hot regime.
- p99.9 on 1d swings with vol (6.8% in 2026Q3 → 24.5% in 2024Q4): the *scale*
  of the extreme moves drifts with σ, but their *relative* rarity (the 3σ
  tail) is constant.
- Trend: 1d kurtosis Kendall τ = −0.09, p = 0.70 — **no drift**.

**Verdict: the "fat tails" finding is the most time-stable property in the
whole experiment.** What changes is the scale (σ), not the shape.

## 3. Event frequency — **tracks volatility, not constant.**

3σ events per quarter (1d, pooled count): 2023Q1–Q3 nearly zero (0–4),
2024Q1 18 → **2024Q4 27** → 2025Q1 19 → fading to 8 (2026Q2) and **0**
(2026Q3). Event rate per 1,000 candles ranges ~0–38.

**Verdict: extreme moves are ~10× more likely in a hot quarter than a quiet
one. Any "expected events per month" number is regime-dependent.**

## 4. Pattern stability — **weekday effect is NOT stable; crash reversion mostly is.**

### 4a. Weekday effect (ag-06: Mon/Wed-down, Thu/Sun-up) — **FLIPS SIGN per quarter.**

Per-quarter effect size = pooled median intraday `(c−o)/o` on {Thu,Sun} minus
on {Mon,Wed}:

| Regime | # quarters | effect positive | effect negative |
|---|---|---|---|
| all 1d quarters | 15 | **5** | **10** |
| 2023–2024 | 8 | 3 | 5 |
| 2025–2026 | 7 | 2 | 5 |

- The sign is positive (Thu/Sun up > Mon/Wed up) in only **5/15 quarters**;
  coin-level agreement (>half of coins) also only **5/15**.
- The 2026 quarters are *inverted* relative to the whole-sample story:
  **2026Q1 effect −2.58%** (Mon/Wed *up*, Thu/Sun *down*, 0/12 coins agreeing
  with the pattern), 2026Q3 +1.12% (12/12 — back to the pattern).
- This is consistent with ag-06's own finding: in the OOS window Monday was
  **+0.28%** intraday and Thursday **−1.10%** — the opposite of the
  Mon/Wed-down Thu/Sun-up rulebook. My quarterly split shows that inversion is
  not a one-off: the effect has flipped several times since 2023.
- Whole-sample medians still show the classic shape (ret_next: Mon −0.42%,
  Wed −0.60%, Thu +0.20%, Sun +0.28%; intraday: Tue −0.43%, Thu −0.59%) — so
  the pattern is real *on average* but **not time-stable**: it averages out
  across quarters while being absent or inverted in most of them.

**Verdict: the weekday direction effect does NOT survive a quarterly split.
It is a full-sample average that hides sign-flips across regimes. Not a stable
edge.**

### 4b. Daily-crash reversion (ag-07: buy 1d down-3σ crash, next-5 positive) — **MOSTLY STABLE.**

| Quarter | n events | median next-5 % | baseline (all candles) % |
|---|---|---|---|
| 2024Q1 | 5 | +8.59 | +1.56 |
| 2024Q2 | 4 | **−3.99** | −1.30 |
| 2025Q1 | 11 | **−2.58** | −2.52 |
| 2025Q4 | 8 | +2.63 | −1.84 |
| 2026Q1 | 9 | +8.33 | −2.23 |
| other quarters | 1–3 ea | positive | — |

- **8 of 10 quarters with any crash events show positive median next-5
  returns** (mean same). The two negative quarters (2024Q2, 2025Q1) are both
  periods when the *whole market* was falling (baseline also −1.3% to −2.5%) —
  crashes there just followed the market down instead of reverting.
- Full-sample result reproduces exactly: 46 down events, next-5 mean **+2.47%**,
  median **+3.07%** vs a −0.15% median baseline (identical to ag-07).
- Caveat: per-quarter n is tiny (1–11 events). The reversion is a real
  tendency, not a guarantee in every regime.

**Verdict: crash reversion is the most regime-robust directional pattern in
the experiment — it holds in most quarters and only fails when the market
itself is in a sustained decline.**

## 5. Bottom line: stationary?

| Property | Stable? | How it drifts |
|---|---|---|
| Volatility level | **No** | regime cycles 2.0% ↔ 6.2% (1d σ), no monotonic trend |
| Fat tails (kurtosis) | **Yes** | kurtosis > 3 in all 15 quarters |
| Tail *scale* (p99.9) | No | tracks σ (6.8% ↔ 24.5%) |
| 3σ-event frequency | No | ~0 to ~38 per 1,000 candles |
| Weekday effect | **No** | sign flips; 5/15 quarters match |
| Crash reversion | **Mostly yes** | 8/10 quarters positive; fails only in down-markets |

**Answer: the distribution is NOT stationary.** Volatility, tail scale, and
event frequency drift with the market regime (2023 quiet → 2024/early-2025
active → 2026 cooling). But the *relative* properties are remarkably stable:
returns are fat-tailed in every quarter, and daily-crash reversion holds in
most regimes. The **weekday direction pattern is the least time-stable
finding** — it flips sign by quarter and should be treated as a statistical
artifact of the full sample, not a persistent edge.

Practical consequence for a live edge: size on **adaptive** volatility (rolling
σ, as ag-11 already proposes), expect event counts to vary ~10×, keep the
crash-reversion thesis (it's the survivor), and do **not** anchor any strategy
on the weekday tilt.

Data: `output/quarters.csv` (per coin/tf/quarter σ, kurtosis, p99.9, 3σ
counts), `output/pattern_stability.csv` (per-quarter weekday effect + crash
reversion), `output/trend_test.csv`, charts in `output/charts/`.
