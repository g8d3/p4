# ag-03 — Conditional tails: is the extreme predictable?

**Question**: does the *next* candle's return distribution — especially its
extreme tail — change given what just happened?

**Data**: `../ag-01-data/output/candles_raw.csv`, 12 coins × 4 timeframes
(5m / 1h / 1d / 1w), 135,232 rows, zero gaps (verified in manifest). Returns
`ret = (c[t]-c[t-1])/c[t-1]` and `range = (h-l)/l` computed per `(coin, tf)`
ordered by time; `ret[t+1]` is the response variable.

**Method**: for each signal, `ret[t+1]` is compared for signal-present vs
signal-absent vs the unconditional distribution. Stats per group: n, mean,
stdev, p50/p90/p99/p99.9 of `ret[t+1]`. Significance: Mann-Whitney U
(yes vs no) + bootstrap 95% CI on the yes-group p99. Because per-coin tail
samples are thin (see table), results are evaluated at two levels:

1. **Per `(coin, tf)`** — full table in `cond_next.csv` (columns per spec,
   plus `mw_p`, `p99_ci_lo`, `p99_ci_hi`). Small n = caveat, not a result.
2. **Pooled across coins** (`coin=ALL` rows) — returns normalized to z-scores
   per `(coin, tf)` and pooled within each tf. This is where `n ≥ 300` is
   actually met for 5m/1h.

Per-coin sample adequacy (min yes-group n across all signals, per pair):
most tail signals (3σ, vol_top1, range_top1, 5-consec) sit well below
`n=300` at the single-coin level. Only `range_top10` on 5m/1h reaches
`n ≥ 300` in 24 of 48 pairs. **Every verdict below rests primarily on the
pooled rows**; the per-coin table is the raw material.

---

## Signal-by-signal findings

### 1. Extreme previous move (`ret[t] > +2σ / < −2σ / > +3σ / < −3σ`)

**Verdict: no directional edge — but volatility clusters after extremes.**
The center of the distribution barely moves; the *dispersion* widens a lot.

Pooled (z-scores), per tf — yes-group vs base:

| signal | tf | n_yes | mean_next | p50_next | stdev_next | p99_next | p99_ci | base p99 | MW p |
|---|---|---|---|---|---|---|---|---|---|
| ret < −3σ | 5m | 425 | +0.19 | +0.35 | 1.94 | 5.21 | [4.4, 5.8] | 2.83 | 1.8e-05 |
| ret < −3σ | 1h | 494 | +0.35 | +0.33 | 2.28 | 6.38 | [5.4, 8.0] | 2.94 | 6.2e-06 |
| ret < −3σ | 1d | 54 | +0.83 | +0.46 | 2.10 | 6.51 | [4.3, 6.7] | 2.99 | 1.4e-03 |
| ret > +3σ | 5m | 498 | −0.01 | −0.19 | 1.71 | 4.35 | [3.9, 6.0] | 2.83 | 3.6e-02 |
| ret > +3σ | 1h | 555 | +0.02 | −0.06 | 1.97 | 5.66 | [4.7, 6.4] | 2.94 | 5.0e-01 |
| ret > +3σ | 1d | 133 | −0.19 | −0.29 | 1.88 | 5.41 | [3.6, 6.0] | 2.99 | 7.8e-02 |
| ret < −2σ | 1h | 1543 | +0.14 | +0.15 | 1.78 | 5.26 | [4.8, 5.7] | 2.94 | 9.5e-08 |
| ret > +2σ | 1h | 1657 | −0.06 | −0.14 | 1.63 | 4.85 | [4.4, 5.4] | 2.94 | 7.2e-06 |

Reading:

- **After a big DOWN candle** the next return's *center* shifts **up**
  (p50_next +0.35σ on 5m, +0.33σ on 1h, +0.46σ on 1d for the −3σ signal) —
  a short-term **reversion/bounce** in the median, statistically significant
  by MW. The direction effect is the opposite of momentum.
- **After a big UP candle** the center shifts only slightly down (p50_next
  −0.14σ, −0.19σ on 5m) — mild reversion, not consistently significant.
- **Both directions** show the far tail *widening*: p99_next is 1.5–2.2× the
  base p99 (5m/1h/1d), and the bootstrap CI for the yes-group p99 excludes the
  base p99 in every adequate-n case. stdev_next is 1.6–2.3× base.
- Per-coin aggregates (48 pairs/signal): p99_ratio > 1 in **35/48** (+2σ),
  **32/48** (−2σ), **27/48** (+3σ), **29/48** (−3σ); median stdev_ratio
  1.46–2.01. Direction of the p50 shift is consistently **reversion after
  down, slight reversion after up** — no momentum anywhere.

**Conclusion**: extremes are followed by *wider* distributions (vol
clustering) but the *sign* of the next move is not predictable enough to
trade. The positive p50 after down-extremes is real but small (0.1–0.5σ) and
it fights the equally real risk of a much bigger adverse move (p99 is 2×).

### 2. Volatility state (`range[t]` in top decile / top percentile)

**Verdict: vol clustering is REAL, strong, and the cleanest effect in the
whole experiment.**

Pooled (z-scores):

| signal | tf | n_yes | mean_next | stdev_next | p99_next | p99_ci | base p99 | MW p |
|---|---|---|---|---|---|---|---|---|
| range top1% | 1h | 604 | +0.35 | 2.53 | 7.84 | [6.1, 8.8] | 2.94 | 2.6e-04 |
| range top1% | 5m | 612 | +0.10 | 2.09 | 5.67 | [4.4, 6.7] | 2.83 | 1.3e-01 |
| range top1% | 1d | 139 | +0.27 | 1.90 | 5.61 | [4.5, 6.3] | 2.99 | 1.1e-01 |
| range top10% | 1h | 6004 | +0.04 | 1.69 | 5.08 | [4.7, 5.4] | 2.94 | 4.5e-01 |
| range top10% | 1d | 1303 | +0.11 | 1.49 | 4.41 | [4.1, 5.1] | 2.99 | 5.1e-02 |
| range top10% | 5m | 6031 | +0.00 | 1.53 | 4.04 | [3.8, 4.3] | 2.83 | 8.9e-01 |

- After a **top-1% range candle**, the next candle's stdev is **2.1–2.5×**
  the unconditional stdev (5m: 2.09, 1h: 2.53, 1d: 1.90) and p99_next is
  **1.9–2.7×** base (1h p99 7.84 vs 2.94; p99.9 9.02 vs 5.49).
- `|ret_next|` mean after a top-1% range candle is **2.0× (1d), 2.8× (1h),
  2.1× (5m)** the unconditional `|ret|` — the clearest single number in the
  experiment.
- Per-coin (24 pairs on 5m/1h, the only level with `n ≥ 300`): p99_ratio > 1
  in **37/48** pairs (top10%), median ratio **1.40**, median stdev_ratio
  **1.48**. The effect is consistent across essentially every coin/tf — see
  `cond_next.csv` (e.g. ZEC 1h range_top1: p99 11.3 vs base 3.8, 3.9×).
- Direction (mean/p50_next) stays near zero → **no directional edge**, only
  dispersion.

**Conclusion**: high-range candles cluster in time. This is the measurable,
exploitable effect — for volatility/range work (e022-style), not for
direction.

### 3. Volume spike (`v[t]` in top percentile)

**Verdict: same as #2 — vol clustering via volume, slightly weaker.**

- 1h: n_yes=604, stdev_next 2.49 vs base 1.00, p99_next 7.84 vs 2.94
  (identical to range_top1 — volume spikes and range spikes are largely the
  same candles), MW p=3.4e-02.
- 5m: stdev_next 1.79 vs 1.00, p99_next 4.68 vs 2.83, p99.9 8.65 vs 4.95,
  `|ret_next|` 1.84× base. MW p=0.10.
- 1d: `|ret_next|` 1.90× base, p99 4.85 vs 2.99 (MW p=4.8e-03, driven by a
  *downside* tilt in the mean, −0.19).
- Per-coin median stdev_ratio 1.75, p99_ratio > 1 in 28/48 pairs.

Volume adds little beyond range; it is a weaker proxy for the same
vol-clustering effect.

### 4. Direction + size (5 consecutive up / down candles)

**Verdict: insufficient data → no robust edge.** Directional streaks are
rare (pooled n=278–1598 across tfs) and thin per coin (0 pairs reach
`n ≥ 300`).

- **5 consecutive DOWN candles**: pooled 1d n=278, p99_next **0.91×** base
  (2.73 vs 3.01), p99.9 **0.67×**, p50_next +0.14, mean +0.15 (MW p=9.2e-04) →
  a reversion signature: after 5 red candles the next candle is smaller and
  centered positive. Same shape on 1h (p99 2.94 vs 2.94 ≈ flat) and 5m
  (p99 3.59 vs 2.81, p50 +0.02). Direction of the p99 shift flips across tf
  (down on 1d/1h, up on 5m) → not trustworthy.
- **5 consecutive UP candles**: pooled p99_next ~1.0–1.1× base across tfs,
  p99.9 *below* base (0.66–0.89× on 1d/5m/1h), p50 slightly negative on
  5m/1h. Statistically significant only on 1h (MW p=5.3e-05) and small in
  magnitude. No coherent edge.

Per-coin: only 2/48 pairs show MW p<0.05 for dn5 and 7/48 for up5 — no
consistency. This signal class is **insufficient data** at current history
lengths.

---

## Overall conclusion

**The extreme is not directionally predictable — but it is volatility-
predictable.**

1. **No momentum edge, no exploitable direction edge.** After ±2σ/±3σ moves,
   after high-range or high-volume candles, after 5-candle streaks, the next
   candle's *expected sign* never shifts by more than ~0.3σ and the sign is
   inconsistent across timeframes. Close-to-close returns behave near-random
   for direction, consistent with the honest-null hypothesis in the
   experiment design.
2. **Volatility clustering is the real, robust, measurable effect.**
   After an extreme (range, volume, or return) candle, the next candle's
   stdev is 1.5–2.5× unconditional and its p99 is 1.5–2.7× unconditional,
   confirmed at both the pooled and per-coin level and in the far tail
   (p99.9 on 5m: 8.2–8.6σ vs 4.8–5.0σ base). Extremes cluster in time.
3. **Strategic implication**: this experiment tells the strategy where NOT
   to spend capital — betting on directional continuation of extreme moves
   has no measurable edge. The conditional dispersion shift validates
   range/vol-based work (e.g. e022, vol-targeting) as the realistic direction:
   the edge is in *sizing* around clustered volatility, not in predicting the
   sign of the next move.

Caveats: 1w has only ~190 candles per coin and every 1w signal group is
`n<300` — 1w is descriptively included but no verdict rests on it. Per-coin
tail signals (3σ, top1%) are under `n=300` and are used only in aggregate.
All pooled numbers above use z-scored returns so scales are comparable.
