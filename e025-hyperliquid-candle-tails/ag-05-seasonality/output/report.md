# ag-05 — Seasonality & conditionals: calendar + volume patterns

Date: 2026-08-13
Input: `../ag-01-data/output/candles_raw.csv` (135,232 rows; 3,175 v=0
synthetic pre-listing rows dropped → 132,057). 12 coins × 4 tfs. Pooled
rows after dropping first candle + last (no `ret`/`ret_next`):
5m 60,289 · 1h 60,026 · 1d 10,262 · 1w 1,480.

Method: per `(coin, tf)`, ordered by time — `ret = (c[t]-c[t-1])/c[t-1]×100`,
`range = (h-l)/l×100`, `body = (c-l)/(h-l)`. Features bucketed per candle,
target = **next** candle (`ret_next`, `|ret_next|`, `range_next`). Every
feature × tf split 50/50 by time per `(coin, tf)`; a pattern is called real
only if the bucket ordering/effect **replicates in both halves** (Spearman
rho on half-1 vs half-2 bucket stats, buckets with n≥30 in each half).
Negatively-signed rho = halves disagree = noise.

**Robustness bar** (AGENTS.md): an effect is robust only if it replicates in
the **majority of the 12 coins AND in both split halves**. Replication rate =
fraction of coins where the feature's defining effect (bucket-group difference
on the target, per effect list in `bin/analyze.py`) has the same sign as the
pooled effect. Per-coin rows in `patterns_by_coin.csv` (n≥30 per coin bucket;
per-coin p90/p99 kept pooled-only, written only where n≥300).

**Replication rates (per feature × tf):**

| Feature | tf | Metric | Rate | Exceptions (sign inverted) |
|---|---|---|---|---|
| hour | 5m | vol | 12/12 | none |
| hour | 1h | vol | 12/12 | none |
| weekday | 1d | dir | 10/12 | LIT, SOL |
| weekday | 1h | vol | 12/12 | none |
| dom | 1d | dir | 7/7* | — (*post-hoc bucket selection; see §3) |
| vol_pct | 5m | vol | 12/12 | none |
| vol_pct | 1h | vol | 12/12 | none |
| vol_pct | 1d | vol | n/a | >99 bucket ~9 obs/coin, per-coin not evaluable |
| vol_chg | 5m | vol | 10/12 | BTC, DOGE |
| vol_chg | 1h | vol | 11/12 | CRV |
| vol_per_move | 5m | vol | 9/12 | CRV, XMR, ZEC |
| vol_per_move | 1h | vol | 10/12 | BTC, XMR |
| vol_ma20 | 5m | vol | 12/12 | none |
| vol_ma20 | 1h | vol | 12/12 | none |
| vol_ma20 | 1d | vol | 4/4 | only 4 coins have n≥30 in >4x bucket; others pooled-only |
| body_pos | 1h | dir | 12/12 | none |
| cooloff | 5m | vol | 12/12 | none |
| cooloff | 1h | vol | 12/12 | none |

Per-coin targets (same stats, minus pooled-only tails) are in
`output/patterns_by_coin.csv`.

---

## 1. hour (UTC, candle open) — 5m, 1h only

- **Volatility: REAL, replicates.** Median `|ret_next|` is U-shaped across
  the day on both tfs (5m vol_rho 0.64, p=0.001; 1h vol_rho 0.60, p=0.002;
  spread 1.75× / 1.58×).
  - 5m: peak 14 UTC `0.116%` (13–16 UTC all ≥0.097), trough 9 UTC `0.066%`
    (5–9 UTC 0.066–0.068).
  - 1h: peak 13 UTC `0.525%`, trough 9 UTC `0.335%` (5–9 UTC 0.333–0.361).
  - Heatmap peaks Tue–Fri 12–15 UTC; lows Sat/Sun early UTC hours. This is
    the US-session-open volatility bump + weekend lull.
- **Direction: FLAT.** Median `ret_next` ≈ 0 all hours; split halves disagree
  for most hours. Max deviation from overall median: 0.010% (5m), 0.062%
  (1h). Only a faint, sub-0.1% overnight-weakness tilt on 1h (hours 1, 9,
  12, 21, 22 negative in both halves). Not a tradeable direction edge.
- **Per-coin replication: 12/12 (5m and 1h).** US-open hours (12–16 UTC)
  have higher next-candle volatility than the Asian trough (5–9 UTC) in
  every one of the 12 coins. No exceptions; no single coin drives the pooled
  U-shape.
- **Verdict:** volatility effect real and chartable; direction flat. This
  confirms the ag-02/ag-03 expectation.

## 2. weekday — 1d direction real; 1h weekend-vol lull real; rest flat

- **1d direction: REAL, replicates 7/7 weekdays, per-coin.** Median
  `ret_next` (12 coins pooled, ~1,460/day): Mon **−0.42%**, Wed **−0.60%**,
  Sat −0.21% · Thu **+0.20%**, Sun **+0.28%**, Tue −0.09%, Fri +0.07%.
  dir_rho 0.893, p=0.007. Every weekday has the same sign in both time
  halves, and the sign holds per coin: Mon negative in 10/12 coins, Wed
  negative in 11/12, Thu positive in 10/12.
- **1d volatility:** Friday median `|ret_next|` 1.31% vs 2.40–2.50%
  Tue/Wed — a large Friday lull (p90 also lowest: 5.63% vs ~7.8%). rho not
  significant (p=0.215, only 7 buckets) but the size is notable.
- **1h volatility: REAL.** Sat 0.283% / Sun 0.327% vs ~0.40–0.45% on
  weekdays (vol_rho 0.893, p=0.007).
- **1h / 5m direction: FLAT.** Split halves conflict (e.g. 1h Sun h1 −0.045,
  h2 +0.026). Not robust.
- **1w degenerate** — all weekly candles open Monday 00:00 UTC.
- **Verdict:** the only calendar **direction** pattern in this experiment,
  and it replicates out-of-sample and per-coin. Caveat: driven by the daily
  close/rollover calendar, not intraday; ~2.3y per half. Worth a dedicated
  check in a follow-up.

## 3. dom (day of month) — NOTHING

- Median `ret_next` swings ±0.8% across days but the ordering does not
  replicate across halves (1d dir_rho 0.178 p=0.34; 1h −0.151). Volatility
  flat to noise (1d vol_rho 0.31 p=0.09).
- **Verdict:** no effect. Expected — reported as null.

## 4. vol_pct (volume percentile within coin,tf) — vol REAL; direction flat

- **Volatility: REAL, strong, monotonic, replicates.** 5m median `|ret_next|`
  by bucket: `<50` 0.066% → `50-90` 0.089% → `90-99` 0.113% → `>99` 0.163%
  (vol_rho 1.00, p<0.001, 2.45×). 1h: 0.312 → 0.451 → 0.635 → 1.058
  (vol_rho 1.00, p<0.001, 3.39×).
- **Direction: FLAT / inconsistent.** Within-bucket medians ≈ 0 except the
  `>99` bucket: positive on 5m (+0.021/+0.016 both halves) and 1h
  (+0.142/+0.038), but **negative** on 1d (−1.06/−1.60, n=109). Same extreme
  bucket flips sign across tfs → direction effect not established.
- **Verdict:** volume percentile is the strongest single volatility
  predictor tested and replicates cleanly; no direction edge.

## 5. vol_chg (volume change decile) — NOTHING

- All rho low or negative (1h vol_rho 0.48 p=0.16; 5m 0.44 p=0.20). The one
  significant-looking metric, 1w dir_rho −0.90, is **anti-replication**:
  half-1 and half-2 bucket medians are opposite-signed (e.g. D10 h1 +3.54,
  h2 −2.11) → noise. Volatility spread ≤1.4×.
- **Verdict:** no effect.

## 6. vol_per_move (v / |ret|, percentile) — NOTHING

- No metric survives: 1h vol_rho 0.80 p=0.20 (4 buckets, not significant);
  1d dir_rho +1.0 is 3 buckets only; 5m/1w conflict. Volatility spread
  ≤1.2×.
- **Verdict:** no effect.

## 7. vol_ma20 (v vs trailing 20-period median) — vol REAL; direction flat

- **Volatility: REAL, monotonic, replicates.** 1h: `<0.5x` 0.335% → `0.5-1x`
  0.361 → `1-2x` 0.407 → `2-4x` 0.447 → `>4x` 0.495 (vol_rho 1.00, p<0.001,
  1.48×). 1d: 1.91 → 2.01 → 2.25 → 2.47 → 2.91 (vol_rho 1.00, p<0.001,
  1.52×). 5m: rho 0.90 p=0.037 (weaker, 1.18×).
- **Direction: FLAT.** 1d halves conflict (2–4x: h1 +0.334 h2 −0.334; >4x:
  h1 +0.326 h2 −0.272); 1h `>4x` h1 −0.005 / h2 +0.027 conflict; 5m all ≈ 0.
- **Verdict:** relative volume level predicts next-candle volatility
  (consistent with vol_pct) and replicates; direction flat.

## 8. body_pos (close position in range) — mild mean-reversion on 1h only

- **1h direction: mild but replicated.** Median `ret_next`: lower wick
  +0.010% (h1 +0.003 / h2 +0.019), mid −0.009% (both −), upper wick −0.032%
  (h1 −0.039 / h2 −0.025). dir_rho 1.00, p<0.001. Candles closing near the
  high are followed by below-average returns — a weak intraday pullback
  effect. Magnitude ~0.04%: real but small.
- **Other tfs:** 5m flat (medians ≈ 0); 1d upper-wick negative replicates
  (−0.51/−0.46) but lower-wick conflicts; 1w contradicts (upper positive,
  n=191). Not consistent across tfs.
- **Verdict:** mild reversion on 1h; treat as suggestive, not structural.

## 9. cooloff (periods since |ret| ≥ 2σ) — volatility clustering REAL

- **Volatility: REAL, replicates, decays with time.** Median `|ret_next|`
  by bucket — 5m: `0` (just moved) 0.144% → `1-2` 0.113 → `3-5` 0.105 →
  `6+` 0.071 (vol_rho 1.00, p<0.001, 2.05×). 1h: 0.759 → 0.593 → 0.481 →
  0.346 (vol_rho 1.00, p<0.001, 2.20×). Volatility after a 2σ candle is
  ~2× baseline and mean-reverts over ~6+ candles.
- **Direction: FLAT.** 1h bucket-0 split halves conflict (−0.018/+0.014);
  5m tiny positive (0.005/0.003) but negligible vs baseline.
- **Verdict:** confirms ag-03's volatility-clustering finding at every
  timeframe; no directional follow-through.

---

## Overall conclusion

| Feature | Volatility | Direction |
|---|---|---|
| hour (5m/1h) | **real** (U-shape, US-open bump) | flat |
| weekday | real: Sat/Sun lull on 1h; 1d Friday lull | **real on 1d** (Mon/Wed down, Thu/Sun up; 7/7 replicate) |
| dom | nothing | nothing |
| vol_pct | **real** (monotonic, 2.4–3.4×) | flat / inconsistent |
| vol_chg | nothing | nothing |
| vol_per_move | nothing | nothing |
| vol_ma20 | **real** (monotonic) | flat |
| body_pos | negligible | mild reversion on 1h only |
| cooloff | **real** (vol clustering, ~2×) | flat |

**Headline:** the strong, replicable seasonality is in **volatility** — the
hour-of-day U-shape, the volume-level effect, and volatility clustering all
replicate out-of-sample. **Directional** edges are almost absent, exactly as
ag-02/ag-03 predicted; the exceptions are the **daily-weekday pattern** (a
genuine, per-coin, both-halves-replicating effect worth a dedicated follow-up)
and a weak 1h body-position reversion. Day-of-month, volume-change, and
volume-per-move show nothing — reported as nulls.
