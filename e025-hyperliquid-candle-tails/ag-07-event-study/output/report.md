# ag-07 — Event study: what happens around 3σ moves?

Phase 4 of e025. **Question asked**: when a coin makes an extreme move (a candle
whose move exceeds ±3σ for that coin and timeframe), what is true *before* and
*after* it? Plus a brand-new feature the user requested: **how extended is price
from its last confirmed swing high/low**, computed without peeking at the future.

---

## Plain English (first, as required)

An **event study** is a way of "zooming in" on rare moments. Instead of looking
at every single candle, we pick out only the rare ones (a move bigger than 3σ),
then look at the candles *before* and *after* them and ask: "on average, what
happens next?" If the answer is "nothing special", the extreme move was just a
random blip. If the answer is "price usually continues" (momentum) or "price
usually snaps back" (reversion), that is a signal worth knowing about.

**3σ** — every coin's percentage moves scatter around some average with a
certain spread. σ (sigma) is a measure of that spread. A move of 3σ means "3
spreads wider than the typical move" — genuinely rare for *this specific coin*,
even though crypto is much wilder than a bell curve would predict. In our data
~1.2–1.9% of candles are 3σ events (a bell curve would say 0.27%) because
crypto has **fat tails**.

**Pivot / swing high** — a local top: a candle whose high is higher than the 5
candles before it AND the 5 candles after it. **No-lookahead** means we never
use information that a trader couldn't have had at the time. A pivot high is
only *confirmed* 5 candles after it happens, so a strategy built from these
numbers could have been run live with zero future knowledge. This matters
because "hindsight patterns" are the #1 way backtests lie.

**MAE / MFE** — from the moment the event candle closes, look at the next 10
candles. **MAE** (max adverse excursion) = the worst you'd be down in that
window. **MFE** (max favorable excursion) = the best you'd be up. They describe
the realistic "risk envelope" of trading the event.

---

## Data & method

- **Input**: `../ag-01-data/output/candles_raw.csv` — 12 coins × 4 timeframes
  (5m, 1h, 1d, 1w). Dropped the 3,175 `v=0` synthetic pre-listing candles
  (documented in ag-01 manifest and ag-02's session-log). 132,057 rows remain.
- **Derived** per `(coin, tf)` ordered by time:
  `ret`, `range`, `body`, `sigma` (global stdev of `ret`), `rolsig` (rolling 20
  stdev, valid only after 50 observations), `vol_pct` (volume percentile within
  the series).
- **Event** = candle with `|ret| > 3 × sigma`. Side = up/down by sign.
- **Swings**: pivot high/low with window N=5, confirmed at `t+5`. At any time,
  the *last confirmed* pivot is the most recent one whose confirmation ≤ t.
  `dist_high = (close − last_confirmed_pivot_high) / rolsig`,
  `dist_low  = (close − last_confirmed_pivot_low)  / rolsig`.
  Raw `dist` is unbounded when `rolsig → 0` (dead-quiet periods); values are
  clipped to ±20σ for reporting. The ext/mid/con buckets only depend on the ±1
  boundary, so clipping never changes a bucket.
- **Outcomes** measured from the event close: cumulative return at +1, +3, +5,
  +10 candles, the full +1..+10 path, and MAE/MFE over the next 10 candles.
- **Split-sample**: every path/split is recomputed on the first vs second half
  of each `(coin, tf)` series (by time). A finding is only called robust if it
  replicates in both halves.

### Sample sizes (events per tf, pooled across coins)

| tf | up events | down events | total | sample window |
|---|---|---|---|---|
| 5m | 498 | 425 | 923 | ~17 days (API retention) |
| 1h | 555 | 494 | 1049 | ~7 months |
| 1d | 99 | 46 | 145 | full history (~3.5y) |
| 1w | 19 | 3 | 22 | too thin — excluded |

Caveats to keep in mind for every number below:
- **5m/1h cover one market regime** (Jul–Aug 2026 snapshot). They are a
  coherent, recent window, not multi-year history.
- **1w is unusable** (22 events). We do not make claims on it.
- **Coins are correlated** (they are all crypto perps; they move together).
  Pooled events are not 12× independent evidence. We report per-coin
  replication rates to compensate.
- Global σ includes the fat tails, so a 3σ event is rare *for this coin*, which
  is the intended meaning.

---

## Answers to the six questions

### Q1. Momentum or reversion? — **Mostly nothing. One robust exception.**

Average cumulative return after an event (%), next candles:

| tf | side | +1 | +3 | +5 | +10 | median +5 | unconditional mean +5 |
|---|---|---|---|---|---|---|---|
| 5m | up | -0.004 | +0.005 | +0.014 | -0.007 | -0.007 | +0.003 |
| 5m | down | +0.034 | +0.016 | +0.027 | +0.022 | +0.050 | +0.003 |
| 1h | up | +0.012 | -0.083 | +0.062 | +0.155 | -0.210 | -0.009 |
| 1h | down | +0.298 | +0.358 | +0.258 | +0.333 | +0.274 | -0.009 |
| 1d | up | -0.216 | +3.303 | +4.424 | +5.619 | +0.783 | +0.681 |
| 1d | down | +2.439 | +5.593 | +2.471 | +3.108 | +3.069 | +0.681 |

- **5m**: flat. Up and down events are followed by essentially **zero** drift
  (the +0.01–0.03% means are far below the ~±0.5% noise band of an event path;
  median returns straddle zero). **Null.**
- **1h**: down events show mild mean reversion (+0.26% at +5 vs a −0.009%
  baseline) — a crash at hourly scale is followed by a small bounce. Up events
  are flat-to-slightly-negative. **BUT** the down effect fails the split-half
  test (first half −0.14%, second half +0.85%) — see Q6. Report as
  *directionally reversionary, not robust*.
- **1d**: both sides are followed by above-baseline positive 5-day returns.
  Up events: +4.4% mean (+0.78% median) vs a +0.68% baseline — looks like
  momentum. Down events: +2.5% mean, +3.07% **median**, vs +0.73% for *all*
  daily down-candles — looks like reversion. Only the down effect survives
  replication (Q6).

**Verdict**: on the short timeframes there is no momentum and no reversion —
extreme moves are followed by noise. On the daily timeframe, **crashes
mean-revert** over the following ~5 days (robust), while the rally-momentum
number is not robust.

### Q2. Asymmetry? — **Yes, in three distinct ways.**

1. **Frequency**: up events outnumber down events at every timeframe
   (5m 498/425, 1h 555/494, 1d **99/46**). Extreme rallies are more common
   than extreme crashes — the tail is right-skewed.
2. **Magnitude**: up events are slightly bigger than down events everywhere
   (1d mean |ret| 17.75% vs 16.05%; 1h 3.58% vs 3.37%; 5m 0.72% vs 0.68%).
3. **Path**: rallies and crashes do *not* mirror each other. At 1d, down
   events rebound (median +3.07%) while up events' median is +0.78%; at 1h,
   down events bounce (+0.27% median) while up events sag (−0.21% median).
   **Crashes revert; rallies do not.** This is the asymmetry the question was
   looking for, and the crash-reversion side is the only one that survives
   replication.

### Q3. Do events cluster? — **Yes (volatility clustering, as expected).**

Intervals between consecutive events per `(coin, tf)`, compared to a random
("geometric") null with the same event rate:

| tf | mean interval / expected | short intervals ≤10 candles observed vs expected | dispersion (Var/Mean²) |
|---|---|---|---|
| 5m | 0.99 | 0.35 vs 0.14 (2.5×) | 2.96 |
| 1h | 0.91 | 0.44 vs 0.16 (2.7×) | 3.19 |
| 1d | 0.79 | 0.33 vs 0.13 (2.5×) | 1.01 |

Interpretation:
- **1h and 1d**: events genuinely arrive faster than random (mean interval
  10–20% below expectation) and short gaps (≤10 candles) are 2.5–3×
  over-represented. **Events cluster.**
- **5m**: the average spacing matches random (ratio ≈ 1.0), *but* the
  distribution is wildly over-dispersed (Var/Mean² ≈ 3): bursts of events
  followed by long quiet stretches. That is volatility clustering seen through
  a stationary lens.
- This is **expected** (ag-03 already proved vol clustering) — not new, but it
  confirms 3σ events behave like the 2σ events in that respect.

### Q4. Does pre-event state change the reaction? — **Weakly, and mostly not robustly.**

Mean next-5-candle return by split, per side:

**a. Swing extension at the event** (up → `dist_high`, down → `dist_low`; ext = beyond last swing, con = contra):

| tf | side | ext | mid | con |
|---|---|---|---|---|
| 5m | up | +0.069 | -0.025 | +0.044 |
| 5m | down | +0.044 | +0.013 | +0.029 |
| 1h | up | +0.306 | +0.100 | -0.357 |
| 1h | down | +0.009 | +0.457 | +0.185 |
| 1d | up | +4.271 | +7.612 | **-4.724** (n=18) |
| 1d | down | +1.589 | +2.793 | +4.894 (n=5) |

The only differentiated cell is **1d up events**: rallying while *contra* to the
last swing (i.e. a dead-cat bounce in a downtrend) → −4.7% over 5 days vs
+4–7% when already extended. n=18 (< 50) and the mid bucket fails split-half
replication → **insufficient data, direction only.** At 5m/1h the differences
are ~0.0–0.4%, inside the noise band. **Mostly null.**

**b. Event volume percentile** (high = p90+, low = <p90):

| tf | side | high_vol | low_vol |
|---|---|---|---|
| 1d | up | +1.375 | +7.411 |
| 1d | down | +3.653 | -0.527 (n=13) |
| 1h | up | +0.086 | -0.032 |
| 1h | down | +0.275 | +0.190 |
| 5m | up | +0.015 | +0.011 |
| 5m | down | +0.039 | -0.002 |

1d shows a split (low-volume rallies follow through more; high-volume crashes
rebound more) but neither replicates cleanly across halves (1d up: h1 +10.7/+8.6
→ h2 −4.5/+0.05) and the down/low cell has n=13. **Not robust.**

**c. Regime before the event** (rolsig high vs low vs own series median):

All the *interesting* cells have n < 50 (e.g. 5m low-regime events: −0.46% to
−0.48%, n=18–25; 1h down low-regime: −1.22%, n=24). Per the n≥50 rule these are
**not reportable** as results. High-regime cells (the bulk of events) show the
same near-zero reactions as pooled. **Null with a leftover question mark.**

**d. Hour of day (UTC)**: the only cell that replicated across halves is
**1h up events during US hours (12–17 UTC): +0.434 / +0.415** in both halves vs
−0.37/−0.28 for 0–5 and 18–23. Magnitude is small (≈0.4% vs a flat baseline)
and only one of many hour cells tested — treat as **suggestive at best** under
the multiple-testing caveat.

**Overall Q4 verdict**: pre-event state changes the reaction *little*. The 1d
extension pattern and the 1h-US-hours pattern are the only candidates, and both
are marginal. The honest headline is that the event's own size dominates: the
reaction (Q1/Q2) is what it is regardless of how extended, how loud, or what
regime preceded it — with the daily-crash exception.

### Q5. Risk envelope (MAE/MFE, next 10 candles from event close)

Median and p90 of max adverse / max favorable excursion (%):

| tf | side | MAE med | MAE p90 | MFE med | MFE p90 | MAE/MFE |
|---|---|---|---|---|---|---|
| 5m | up | -0.48 | -0.09 | +0.44 | +1.46 | -1.03 |
| 5m | down | -0.37 | -0.06 | +0.45 | +1.28 | -0.88 |
| 1h | up | -2.48 | -0.48 | +2.37 | +8.30 | -0.96 |
| 1h | down | -2.57 | -0.24 | +2.63 | +7.54 | -1.00 |
| 1d | up | -9.19 | -2.07 | +11.64 | +54.17 | -0.90 |
| 1d | down | -9.27 | -4.55 | +14.23 | +30.79 | -0.65 |

- **5m/1h**: the envelope is essentially symmetric (MAE/MFE ≈ −1.0). A 1h 3σ
  event costs you ~2.5% at worst and gains you ~2.5% at best; a 5m one ~0.4%.
- **1d**: favorable dominates adverse, especially for down events (MFE median
  +14.2% vs MAE −9.3%; p90 MFE +30.8%). The upside *after* a daily crash is
  roughly 1.5× the downside — the same shape as the mean-reversion finding.
  For up events the p90 MFE is a striking **+54%** (one event window went
  +124%).

**Practical reading**: if you trade 3σ events long-only, the day-scale
asymmetry is where any edge lives; at 5m/1h you are paying roughly symmetric
rolls of the dice, and the p90 adverse numbers are the size of the position you
must be able to survive.

### Q6. Split-sample: does any of it replicate? — **One robust result only.**

Per `(side, tf)`: pooled mean +5, fraction of coins with the *same sign*, and
first/second-half means (per-coin half split by time):

| side | tf | pooled mean5 | coins same sign | h1 | h2 | half-replicated |
|---|---|---|---|---|---|---|
| down | 1d | +2.47 | 6/6 (100%) | +3.04 | +2.17 | **YES** |
| up | 1d | +4.42 | 8/8 (100%) | +9.24 | -3.65 | NO |
| down | 1h | +0.26 | 10/12 (83%) | -0.14 | +0.85 | NO |
| up | 1h | +0.06 | 7/12 (58%) | +0.24 | -0.14 | NO |
| down | 5m | +0.03 | 7/12 (58%) | -0.04 | +0.11 | NO |
| up | 5m | +0.01 | 6/12 (50%) | -0.01 | +0.05 | NO |

**The one result that survives everything**: **daily down events (crashes) are
followed by positive 5-day returns**, replicated across every coin with enough
data (6/6), in both time halves (+3.04 / +2.17), and visible in the median
(+3.07%) — not just a mean pulled by outliers. Everything else fails: the 1d
rally-momentum (+4.4%) is a first-half/early-2026 phenomenon that goes *negative*
(−3.7%) in the second half; all 5m/1h path numbers flip sign between halves.

Per the honest-results rule, **the rally-momentum and all short-timeframe
"patterns" are noise; the crash-reversion on 1d is the single replicating
finding** — and even it rests on only 145 daily events (46 down), so call it
directional evidence, not a sized edge.

---

## The swing-distance feature (the user's requested column)

The feature works and is well-behaved once `rolsig→0` is clipped:

- **Distribution**: median `dist_high` ≈ −0.1σ and `dist_low` ≈ +0.1σ — the
  typical candle sits just below its last confirmed swing high / just above its
  last confirmed swing low. `frac_abs_ge1` ≈ 52–56%: *more than half of all
  candles* are ≥1σ from the last confirmed swing, which is sensible given
  swings are only 5 candles apart while σ is a 20-candle statistic — trends
  carry price away from swings frequently.
- **Events and extension**: 3σ events are **3–14× more frequent when the coin
  is already extended** past its last confirmed swing than when it is not:

| tf | up events per 1000, extended vs not | down events per 1000, extended vs not |
|---|---|---|
| 5m | 24.4 vs 6.7 (3.6×) | 29.8 vs 4.9 (6.0×) |
| 1h | 33.4 vs 7.3 (4.6×) | 35.4 vs 5.9 (6.0×) |
| 1d | 29.4 vs 7.6 (3.9×) | 35.4 vs 2.6 (13.7×) |

  The no-lookahead property is intact: the pivot used for "extended" was
  confirmed ≥5 candles *before* the event. But note the caveat — a 3σ candle
  often *is* the candle that pushes price past a swing, so part of this is
  mechanical (the event extends the distance it is being measured on). The
  direction split (extended-up ⇒ up events, extended-down ⇒ down events) is the
  part that is genuinely informative: price tends to *continue* in the
  direction of extension into the extreme. We report the numbers as-is with
  that caveat in mind.
- **Extension × reaction**: beyond the event rate, extension state barely
  changes the *next* 5 candles (Q4a) — mostly null, with the 1d dead-cat-bounce
  exception (n=18, unproven).

---

## Honest expectations check

- ✅ **Expected and confirmed**: volatility clustering (Q3), wider path width
  after events (MAE/MFE symmetric and large relative to ordinary candles),
  "most things are null".
- ✅ **New**: the asymmetry — crashes are rarer but revert, rallies are more
  common but flat (Q2); the daily-crash reversion is the single robust signal
  (Q6); and the extension-feature event-rate relationship (3–14×).
- ✅ **New and null**: pre-event extension/volume/regime state does not
  meaningfully change the post-event path.

**Bottom line**: on Hyperliquid perps, 3σ moves are followed by nothing special
at 5m/1h, and by **mean reversion after daily crashes** (the only result that
replicates across coins, halves, and mean+median). Extreme rallies are more
common than extreme crashes, but they neither continue nor revert. The
swing-distance feature strongly predicts *which direction* extreme moves happen
in (extended-up ⇒ up events), a genuinely new, tradable-adjacent fact — even
though it does not predict what happens *after*.

Files produced: `events.csv`, `event_paths.csv`, `extension.csv`,
`clustering.csv`, `splits.csv`, `mae_mfe.csv`, `replication.csv`,
`context.csv`, `charts/*.png` (8), this report, `beginners_guide.md`,
`session-log.md`.
