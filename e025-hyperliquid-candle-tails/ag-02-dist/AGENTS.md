# ag-02 — Distribution: histograms, quantiles, tail shape

Turn the raw candle table into the empirical distribution of percentage moves:
per-timeframe histograms, heavy-tail statistics, and a findings report.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, data formats
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Inputs

- `../ag-01-data/output/candles_raw.csv` — columns `coin,tf,t_ms,o,h,l,c,v`
- Sort by `(coin, tf, t_ms)` before computing anything time-dependent.

## Derived columns

```
ret   = (c[t] − c[t−1]) / c[t−1] × 100     close-to-close %, per (coin, tf)
range = (h − l) / l × 100                  intra-candle volatility %
```

Compute per `(coin, tf)` group, ordered by time. The first candle of each group
has no `ret` — drop it for stats.

## Deliverables

| File | Contents |
|---|---|
| `output/stats.csv` | Per `(coin,tf)`: `n, mean, stdev, skew, kurtosis, p50, p90, p99, p99.9, min, max` of `ret` |
| `output/hist_<tf>.csv` | One per tf, pooled across coins: `bucket_low, bucket_high, count` (equal-width buckets, ~60 bins, centered on 0) |
| `output/charts/*.png` | Per-tf histogram + one overlay chart comparing tail heaviness (log y-axis shows the tails) |
| `output/report.md` | Findings: are returns fat-tailed? Which tf is most extreme? Any coin outlier? |
| `output/session-log.md` | **A/B test data**: start/end timestamps, command count, every problem hit + how solved, anything that consumed extra context |

## Analysis rules

- **Never pool timeframes** — one histogram per tf. If you must compare across
  tf, normalize returns to z-scores per `(coin, tf)` first.
- **Fat tails test**: kurtosis > 3, and p99.9 far outside ±4σ. Report both
  unconditionally and per coin.
- Visualize tails on log-y so p99/p99.9 events are visible, not squashed.
- `report.md` must state concrete numbers (e.g. "BTC 5m kurtosis = X, p99.9 =
  Y%"), not adjectives. This report feeds the edge analysis in ag-03.

## Tools

- Python 3 + pandas + matplotlib. If the system pandas is missing, create a
  venv with `uv` (`uv venv .venv && uv pip install --python .venv/bin/python
  pandas matplotlib`).

## Command execution

- The analysis is seconds-to-minutes; still run it with a generous timeout
  (`timeout 600`) and background + self-wake per fundamentals.
- Verify outputs exist and are non-trivial (`wc -l stats.csv`, PNGs open and
  have content) before writing `done.txt`.

## Self-command

```bash
( sleep 60; tmux send-keys -t 25-2 "Self-wake: check analysis progress. Files produced? errors? done?" Enter ) &
```

Window: `25-2`. On wake, check outputs, fix errors, iterate until all four
deliverables exist, then write `done.txt` with the headline stats (n per tf,
kurtosis range, p99.9 range).

## Notify (mandatory)
In addition to writing `done.txt`, agents MUST notify on completion:
`notify.sh done "<agent> finished: <headline>"` (from `../../e000-fundamentals/bin/notify.sh`)
On an unrecoverable failure, before giving up: `notify.sh error "<agent> failed: <cause>"`

