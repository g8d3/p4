# ag-05 — Seasonality & conditionals: calendar + volume patterns

Phase 2 of e025: find which **calendar and volume conditions** shift the
next-candle distribution (direction, volatility, range), chart every one, and
validate that any pattern found replicates out-of-sample.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope + A/B findings
- [../ag-02-dist/AGENTS.md](../ag-02-dist/AGENTS.md) — derived column definitions (`ret`, `range`)
- [../ag-03-cond/AGENTS.md](../ag-03-cond/AGENTS.md) — decision rules, honest-results rule

Single agent by design — the e025 A/B test (comparison.md) found 1 agent wins
for jobs this size. Read the shared CSV; never download.

## Hard rules

- **Never download.** Input is `../ag-01-data/output/candles_raw.csv`. If it
  doesn't exist, stop and report.
- **Drop v=0 rows** (3,175 synthetic pre-listing candles) before computing
  anything — ag-02's finding, documented in its session-log.
- **UTC everywhere.** Hyperliquid candle `t` is epoch ms → UTC directly. No
  local-timezone conversions.

## Input

`../ag-01-data/output/candles_raw.csv` — `coin,tf,t_ms,o,h,l,c,v`.

Compute per `(coin, tf)`, ordered by time, dropping the first candle of each
group:
```
ret    = (c[t] − c[t−1]) / c[t−1] × 100
range  = (h − l) / l × 100
body   = (c − l) / (h − l)              # close position in range 0..1
```

## Features (groups) to test

**Calendar**
1. `hour` — hour of day UTC (0–23) of candle open
2. `weekday` — Mon..Sun of candle open
3. `dom` — day of month (1–31)
4. `hour_x_weekday` — heatmap feature (volume + volatility only)

**Volume**
5. `vol_pct` — volume percentile of this candle within its own `(coin,tf)`
   series (buckets: <50, 50–90, 90–99, >99)
6. `vol_chg` — `(v[t] − v[t−1]) / v[t−1]` buckets (deciles or sign+magnitude)
7. `vol_per_move` — `v[t] / |ret[t]|` (liquidity per unit of move), percentile
   buckets
8. `vol_ma20` — `v[t]` vs trailing 20-period median volume (ratio buckets)

**Price-shape (added by design)**
9. `body_pos` — body position buckets: `[0,0.15]` lower wick / `[0.15,0.85]`
   mid / `[0.85,1]` upper wick
10. `cooloff` — periods since last `|ret| ≥ 2σ` (0, 1–2, 3–5, 6+)

## Targets

For each feature bucket, report **all three** next-period stats:
- `ret_next` — direction (mean, median)
- `|ret_next|` — volatility (median, p90, p99)
- `range_next` — volatility proxy (median, p90)

## Deliverables

| File | Contents |
|---|---|
| `output/patterns.csv` | Per `(feature, bucket, tf)`: `n, mean_next, median_next, p90_next, p99_next, |mean|_next, median_abs_next, split1_median, split2_median` |
| `output/patterns_by_coin.csv` | **Per-coin breakdown**: per `(coin, feature, bucket, tf)` — same target stats, at least for features with adequate per-coin n (calendar, vol buckets) |
| `output/charts/*.png` | One chart per feature per tf (bar per bucket, error bars) + `hour_x_weekday` volume and volatility heatmaps. ~12 charts |
| `output/report.md` | Per feature: finding, numbers, replication verdict. **Must state per-coin replication rate** |
| `output/session-log.md` | Per e025 A/B conventions (timestamps, commands, problems) |

## Coin as a grouping variable (mandatory)

The coin IS a dimension. Pooling hides or invents patterns (meme coins vs BTC,
new listings, different volume profiles). Every feature must ALSO be analyzed
per coin, and the report must answer: **"does this pattern hold across coins?"**

1. `patterns_by_coin.csv`: per-`(coin, feature, bucket, tf)` rows with the same
   target stats. Calendar and volume-bucket features have thousands of obs per
   coin — per-coin analysis is fine. Tail quantiles per coin stay pooled-only
   (n<300 rule from ag-03).
2. **Replication rate**: for each `(feature, tf)`, compute the fraction of
   coins where the effect goes in the SAME direction (e.g. "higher vol after
   top-decile volume: 10/12 coins"). Report it explicitly.
3. **Robustness bar**: an effect is robust only if it replicates in the
   majority of coins AND in both split halves. If 3 coins drive the pooled
   result and 9 are flat, that is NOT a pattern — name the exceptions.

## Split-sample validation (non-negotiable)

For every feature × tf, split the series 50/50 by time:
- Compute the bucket target stats on the **first half** and **second half**
  separately.
- A pattern is only reported as real if the bucket ordering/effect **replicates
  in both halves** (same direction of effect). If only one half shows it, call
  it noise. This is the multiple-testing guard — 24 hours × 7 days × 31 days ×
  buckets × 4 tfs is hundreds of tests; most "signals" will be chance.

## Run order (declare before computing)

State in session-log.md the exact feature/target/tf test grid BEFORE running.
A grid added after seeing results is p-hacking — don't.

## Honest-results rule

Expected, based on ag-02/ag-03 findings:
- **Hour-of-day and volume buckets will show strong volatility effects** — that
  is the real, chartable pattern.
- **Mean direction per hour/day will be mostly flat** — do not manufacture a
  story from noise; report it as flat if split-halves disagree.
- **Day-of-month likely nothing.**
- If a feature shows nothing, that IS the result. Say so plainly.

## Command execution

- Python + pandas + scipy + matplotlib (all present system-wide, verified in
  ag-04). Run analysis backgrounded with `timeout 600` + self-wake per
  fundamentals.
- Verify every deliverable exists and is non-trivial before `done.txt`
  (`wc -l patterns.csv`, PNGs valid via `file`).

## Self-command

```bash
( sleep 60; tmux send-keys -t 25-5 "Self-wake: check analysis progress. Files produced? errors? done?" Enter ) &
```

Window: `25-5`. On wake: check outputs, fix errors, iterate. When all
deliverables exist, write `done.txt` with the headline findings per feature.

## Notify (mandatory)
In addition to writing `done.txt`, agents MUST notify on completion:
`notify.sh done "<agent> finished: <headline>"` (from `../../e000-fundamentals/bin/notify.sh`)
On an unrecoverable failure, before giving up: `notify.sh error "<agent> failed: <cause>"`

