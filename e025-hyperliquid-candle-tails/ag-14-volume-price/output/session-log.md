# ag-14 — Session log

## Start / end
- Start: 2026-08-14 09:55 (UTC-5) — window 25-14, opencode-go/deepseek-v4-flash
- End: 2026-08-14 10:15 (UTC-5)

## Declared test grid (signals × buckets × tf) — BEFORE running

Primary timeframe **1d**; secondary sensitivity **1h**. Excluded by design:
5m (ag-13: intraday edges die at 0.09% round trip — not tradeable evidence)
and 1w (too thin per coin). Nothing was added after seeing results.

### Signals, bucket definitions, and replication effects

| # | Signal | Buckets | Headline effect (replication target) |
|---|---|---|---|
| 1 | **Move × volume interaction** | sign(ret[t]) ∈ {up, down} × vol_pct of v[t] within (coin,tf) causal trailing-101 pct → {<50, 50–90, 90–99, >99} = **8 buckets** | E[next1 \| up,vol>90] − E[next1 \| up,vol<50]; same for down |
| 2 | **OBV** | sign(obv_slope10) × sign(price_slope10) → {obv↑price↑, obv↓price↑ (bearish div), obv↑price↓ (bullish div), obv↓price↓} = **4 buckets** | E[next1 \| bearish div] − E[next1 \| obv↑price↑]; bullish div − obv↓price↓ |
| 3 | **VWAP distance** | z = (c−vwap20)/vwap20 / σ(dist) → {z<−1, −1..−0.5, −0.5..0.5, 0.5..1, >1} = **5 buckets** | E[next1 \| z>1] − E[next1 \| z<−1] (reversion if <0) |
| 4 | **Up/down volume ratio** | ratio10 = Σv[up10]/Σv[dn10] → {<0.5, 0.5–0.8, 0.8–1.25, 1.25–2, >2} = **5 buckets** | E[next1 \| ratio>2] − E[next1 \| ratio<0.5] |
| 5 | **Volume-adjusted return** | sign(ret) × quintile of \|ret / (v/median_v)\| within (coin,tf) → **10 buckets** | E[next1 \| up,q5] − E[next1 \| up,q1]; down analog |

### Targets per bucket (per tf, in %)
- `next1` = (c[t+1]/c[t] − 1) × 100 — on 1d: next 1 day; on 1h: next 1 hour
- `next5` = (c[t+5]/c[t] − 1) × 100 — on 1d: next 5 days; on 1h: next 5 hours
- Report mean, median, win rate (frac ret>0) for each; split-sample halves.

### Validation rules (fixed before running)
1. **Split-sample**: each (coin,tf) split 50/50 by time. Pooled effect is real
   only if the headline effect sign replicates in BOTH halves.
2. **Per-coin replication rate**: fraction of the 12 coins where the per-coin
   headline effect sign == pooled effect sign. Coins with n<30 in either
   bucket of the effect are excluded from that effect's rate.
3. **Costs**: breakeven = 0.09% round trip (taker 0.045% × 2, ag-13 model).
   State next to every effect size; only |effect| > 0.09% is net-positive.
4. **No lookahead**: all features from t and before (causal rolling windows,
   trailing percentile); targets t+1 / t+5. OBV uses close-to-close ret sign.
5. Warm-up: OBV slope 10, vwap 20, ratio 10, vol_pct 30 obs dropped (NaN).

### Pitfalls (from AGENTS.md + inherited)
- Drop v=0 (3,175 synthetic pre-listing candles) before computing.
- Volume percentile is per (coin,tf), not absolute (levels differ wildly).
- OBV/VWAP need warm-up; drop NaN/undefined early rows.
- Never pool timeframes in one statistic — separate per tf.
- No single coin's bucket is a pattern; require replication.

## Command count
- Read/ls/head/file checks: 6
- Python runs (analysis, replication, charts): 5 (two `timeout 600`-style
  analyze runs, one replication run, two chart runs — the last analyzed the
  failed chart and re-ran cleanly)
- Data verification one-offs: 4

## What was done
1. Read AGENTS.md + all Inherits (fundamentals, e025 scope, ag-02 derived
   columns, ag-05 split-sample/per-coin replication, ag-13 fee model).
2. Verified input: 135,232 rows, 3,175 v=0 synthetic (matches ag-05's
   documented count), 12 coins, zero duplicates, contiguous coverage.
3. Declared the full test grid in this log BEFORE running (5 signals, exact
   buckets, effects, targets, tfs, validation rules) — nothing post-hoc.
4. `bin/analyze.py` — drop v=0, per-(coin,tf) causal features (trailing
   volume percentile, OBV+slopes, vwap20+σ, up/down ratio, |vol_adj|
   quintiles), next-1/next-5 targets, pooled + per-coin + split-half stats →
   `output/signals.csv` (+ `_features_1d_1h.csv` intermediate).
5. `bin/replication.py` — per declared headline effect: pooled effect, split
   halves, per-coin replication rate (n≥30 rule) → `output/replication.csv`.
6. `bin/charts.py` — 5 bucket-bar charts (1d pooled) + OBV divergence
   illustration on CRV 1d → `output/charts/`.
7. Wrote `output/report.md`, `output/beginners_guide.md`, this log.

## Problems hit + solutions
- **Rolling percentile leak**: initial plan used a naive full-series rank for
  volume percentile; replaced with a causal trailing-101 rolling percentile
  (min_periods=30) so no future info enters bucket assignment. Verified
  groupwise behaviour with a 2-group test first.
- **IntCastingNaNError**: `|vol_adj|` quintile cast failed on NaN (first row
  of each coin has no `ret`). Fixed by masking NaN to float before bucketing.
- **OBV warm-up + boundary**: OBV computed per (coin,tf) group by cumulative
  sum, slope via `np.polyfit` on trailing-10 window; min_periods=10 on all
  rolling windows so the first rows are NaN and dropped — no group leakage.
- **charts.py NameError** (`os` used before import) and **ndarray format
  error** on NaN means — fixed order of imports and cast to float.
- **Chart feature columns missing**: `_features_1d_1h.csv` lacked `c`/`v` for
  the divergence illustration; added both columns to the features dump and
  re-ran analyze.py (idempotent, same numbers).
- **1h effects collapsed** (all ±0.01pp): expected — these are 1d/positional
  effects; reported as secondary sensitivity per the grid, not over-read.

## Verification
- `signals.csv`: 923 rows (pooled + per-coin, n≥30 filtered for coin rows).
- `replication.csv`: 32 effect rows (8 effects × 2 tf × 2 targets) with
  per-coin rates and split-half flags.
- `output/charts/`: 6 PNGs, all valid via `file`; divergence illustration
  data verified numerically (CRV 1d: 178 bearish-div + 96 bullish-div bars
  total, 26/19 in the plotted 230-bar window).
- Key findings double-checked by hand (median per-coin deltas, win-rate
  deltas, named exceptions) before writing report.md.

## Context consumed
- Full e000 AGENTS.md (~1040 lines), e025 + ag-02 + ag-05 + ag-13 AGENTS.md,
  manifest.json, ag-13 edge ledger.
- No downloads, no API calls, no sudo, no extra tmux windows created.

