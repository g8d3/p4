# ag-03 — Conditional tails: is the extreme predictable?

The core research question: does the *next* candle's return distribution —
especially its extreme tail — change given what just happened? If yes, that is
a statistical edge worth building on. If no, that is an honest null result.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, data formats
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../ag-02-dist/AGENTS.md](../ag-02-dist/AGENTS.md) — derived columns and their exact definitions

## Inputs

- `../ag-01-data/output/candles_raw.csv` — raw candles (compute `ret` and `range`
  yourself, same definitions as ag-02, per `(coin, tf)` ordered by time).

## Method

For each signal, split the data into signal-present vs signal-absent, and
compare the **next-candle return tail** (`ret[t+1]`) of the two groups against
the unconditional distribution:

1. **Extreme prev move**: `ret[t] > +2σ`, `< −2σ`, `> +3σ`, `< −3σ` (σ = per
   `(coin,tf)` stdev)
2. **Volatility state**: `range[t]` in top decile, top percentile (volatility
   clustering test)
3. **Volume spike**: `v[t]` in top percentile per `(coin,tf)`
4. **Direction + size**: e.g. 5 consecutive up-candles → next distribution

Deliverable table:

```
output/cond_next.csv
coin | tf | signal | group | n | mean_next | stdev_next | p50_next | p90_next | p99_next | p99.9_next
```

`group` = `yes` (signal present) or `no` / `base` (unconditional).

## Decision rule

A signal is "interesting" when the conditional tail differs from unconditional
in a direction with enough samples to trust it:

- **Sample size**: `n ≥ 300` per group minimum to say anything about p99.
  Report n; small n = caveat, not a result.
- **Shift measure**: compare `p99_next` / `p99.9_next` of the group vs base,
  and report the sign (are extremes followed by more extremes — momentum — or
  smaller moves — reversion?).
- Apply a basic significance check (bootstrap CI on the group's p99, or a
  Mann-Whitney U on the two groups) — a difference of 0.001% on 50 samples is
  noise, not an edge.

## Deliverables

| File | Contents |
|---|---|
| `output/cond_next.csv` | The conditional tail table above |
| `output/report.md` | Per signal: finding + numbers + verdict (edge / no edge / insufficient data). Final section: overall conclusion for the experiment |
| `output/session-log.md` | **A/B test data**: start/end timestamps, command count, every problem hit + how solved, anything that consumed extra context |

## Honest-results rule

The likely outcome on liquid perps is that close-to-close returns are near
random (no edge), and that volatility clustering is the real, measurable
effect (extremes cluster in time). Report what the data says. A clean "no
predictable edge, but vol clusters" is a successful experiment — it tells us
where the strategy should NOT waste capital, and points at range/vol-based
work (like e022) as the realistic direction.

## Command execution

- Python + pandas (see ag-02 for the venv pattern if pandas is missing).
- Run with timeout + background + self-wake per fundamentals. Verify CSV and
  report exist before writing `done.txt`.

## Self-command

```bash
( sleep 60; tmux send-keys -t 25-3 "Self-wake: check analysis progress. Files produced? errors? done?" Enter ) &
```

Window: `25-3`. On wake, check outputs, iterate, then write `done.txt` with the
headline verdict per signal.
