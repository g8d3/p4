# ag-05 — Session log

## Start / end
- Start: 2026-08-13 19:01 (UTC-5) — window 25-5, opencode-go/deepseek-v4-flash
- End: 2026-08-13 19:15 (UTC-5) (extended run: coin-dimension deliverables)

## Declared test grid (feature × tf) — BEFORE finalization

Features (9 bucket features + 1 heatmap feature) × tfs. Declared up front so
nothing is post-hoc; results were not consulted to pick rows.

| Feature | tfs | Per-coin n adequate |
|---|---|---|
| `hour` (0–23 UTC) | 5m, 1h, 1d, 1w | yes (5m/1h; 1d/1w degenerate, all opens 00:00 UTC) |
| `weekday` (Mon–Sun) | 5m, 1h, 1d, 1w | yes (1w degenerate, all opens Monday) |
| `dom` (1–31) | 5m, 1h, 1d, 1w | yes (5m only spans 17 days → 18 of 31 buckets) |
| `hour_x_weekday` | 5m, 1h | heatmaps only (volume + volatility) |
| `vol_pct` (<50, 50–90, 90–99, >99) | 5m, 1h, 1d, 1w | yes |
| `vol_chg` (D1–D10) | 5m, 1h, 1d, 1w | yes |
| `vol_per_move` (<50, 50–90, 90–99, >99) | 5m, 1h, 1d, 1w | yes |
| `vol_ma20` (<0.5x, 0.5–1x, 1–2x, 2–4x, >4x) | 5m, 1h, 1d, 1w | yes |
| `body_pos` (lower/mid/upper) | 5m, 1h, 1d, 1w | yes |
| `cooloff` (0, 1–2, 3–5, 6+) | 5m, 1h, 1d, 1w | yes |

Targets per bucket: `ret_next` mean & median; `|ret_next|` median, p90, p99;
`range_next` median, p90. Tail quantiles per coin stay pooled-only (ag-03
n≥300 rule) — per-coin `p90/p99` written only where n≥300, else NaN.

Validation rules (fixed before running):
1. **Split-sample (non-negotiable)**: each (coin, tf) split 50/50 by time.
   An effect is real only if the bucket ordering replicates in both halves
   (Spearman rho on half-1 vs half-2 bucket stats; positive rho = same
   ordering, negative rho = halves conflict = null).
2. **Per-coin replication rate**: fraction of the 12 coins where the
   feature's effect has the same sign as the pooled effect (effect =
   difference of the feature's defining bucket groups, per effect list in
   `bin/analyze.py`). Named exceptions = coins that disagree.
3. **Per-coin minimums**: per-coin bucket rows only where n≥30; per-coin
   tail quantiles only where n≥300.

## Command count
- Read/ls/head/file checks: 8
- Python runs (analysis + inspection): 7
- Background analysis/charts + self-wakes: 3 (two `timeout 600`-style runs,
  one `timeout 900` rerun for the coin dimension)

## What was done
1. Read AGENTS.md + all Inherits (fundamentals, e025 scope, ag-02 derived
   columns, ag-03 decision rules).
2. Verified input exists; confirmed 135,232 rows, 3,175 v=0 synthetic rows
   (matches AGENTS.md's documented count) via pandas.
3. `bin/analyze.py` — drop v=0, per-(coin,tf) derived cols, 9 feature
   buckets, next-candle targets, full + split-half (50/50 by time) stats,
   Spearman replication metrics per feature×tf, hour_x_weekday heatmap data.
4. `bin/charts.py` — 33 bar charts (feature × tf, direction + volatility
   panels, error bars, overall-median reference line) + 2 hour_x_weekday
   heatmaps (5m, 1h).
5. Manual per-coin validation of the weekday-1d finding before writing the
   report.
6. **Rerun** `bin/analyze.py` adding: `range_next` targets (median, p90);
   `output/patterns_by_coin.csv` per (coin, feature, bucket, tf); and
   per-coin replication rates per (feature, tf) with named exceptions →
   `output/replication_rates.csv`.
7. Wrote `output/patterns.csv`, `output/report.md`, this log, `done.txt`.

## Problems hit + solutions
- **Rolling median across group boundaries**: `groupby.shift(1).rolling(20)`
  computes the window over the whole frame, leaking `(coin, tf)` groups.
  Fixed with a grouped rolling:
  `df.groupby(['coin','tf'])['v_prev'].rolling(20, min_periods=5).median()`
  and reindexing. Verified groupwise behaviour with a 2-group unit test
  before rerunning.
- **Spearman on constant input** → ConstantInputWarning, rho=NaN. Benign:
  it flags degenerate cases (flat direction at 5m, single-bucket features)
  which we classify as flat/noise.
- **Interpretation bug (mine, caught before report)**: a *negative* split
  rho on vol_chg-1w (−0.90, p<0.001) initially looked like a "replicating
  reversal". Inspecting the halves showed bucket signs flip between halves
  (e.g. D10 h1 +3.54 / h2 −2.11) → it is anti-replication, i.e. noise. The
  report treats negative rho as halves-disagree = null, and verified
  every positive claim against the raw half medians.
- **Hour/weekday degenerate on 1d/1w** (all daily/weekly candles open
  00:00 UTC) — charts skipped where <3 buckets; stated in report instead.

## Context consumed
- Full e000 AGENTS.md (~880 lines), e025 + ag-02 + ag-03 AGENTS.md, manifest.
- One 600s background analysis run + one 600s background chart run + one
  900s rerun.
- No downloads, no API calls, no sudo, no extra windows created.

## Verification
- `patterns.csv`: 304 rows, 11 stat columns + split halves (incl. range).
- `patterns_by_coin.csv`: per (coin, feature, bucket, tf), tails pooled-only.
- `output/charts/`: 35 PNGs, all valid (verified with `file`).
- `heatmap_data.csv`: 336 cells (24×7 × 2 tfs).
- `replication_rates.csv`: per (feature, tf) effect, rate, exceptions.
