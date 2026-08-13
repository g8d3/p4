# ag-04 — Monolith: full analysis in ONE agent (Path B)

Path B of the A/B test: one single agent does what Path A splits across
ag-02-dist and ag-03-cond — distribution analysis AND the conditional tail
edge test — in one session, from the shared data.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope + A/B test rules
- [../ag-02-dist/AGENTS.md](../ag-02-dist/AGENTS.md) — derived column definitions, stats spec
- [../ag-03-cond/AGENTS.md](../ag-03-cond/AGENTS.md) — signal definitions, decision rule

## Hard rule: NEVER download

ag-01-data exists precisely so the A/B test runs both paths on identical data.
This agent **must not call the Hyperliquid API**. Read candles only from
`../ag-01-data/output/candles_raw.csv`.

If that file does not exist, STOP and report: "run ag-01-data first". Do not
fetch, do not build a fallback dataset.

## Input

- `../ag-01-data/output/candles_raw.csv` — columns `coin,tf,t_ms,o,h,l,c,v`

## Deliverables (identical file names to Path A, in `output/`)

| File | Spec (from ag-02 + ag-03 AGENTS.md) |
|---|---|
| `stats.csv` | per-`(coin,tf)`: `n, mean, stdev, skew, kurtosis, p50, p90, p99, p99.9, min, max` of `ret` |
| `hist_<tf>.csv` | one per tf, pooled coins: `bucket_low, bucket_high, count`, ~60 equal-width bins centered on 0 |
| `charts/*.png` | per-tf histograms + log-y tail overlay |
| `cond_next.csv` | conditional next-return tail table (signals from ag-03) |
| `report.md` | both findings combined: fat tails per tf, then per-signal edge verdicts |
| `session-log.md` | **A/B test data** (see below) |

## A/B session-log

This is a test artifact as important as the analysis. Record honestly in
`session-log.md`:

- Start and end timestamps
- Command count (shell commands run)
- Every problem encountered and how it was solved (missing pandas? big CSV
  memory? matplotlib headless backend? off-by-one in returns?)
- Where context got heavy (if the model felt the session was getting long,
  note it)
- Number of self-wakes / corrections needed

Do not pad or flatter — the A/B test needs the real numbers.

## Pitfalls (same as Path A)

- Sort by `(coin, tf, t_ms)` before time-dependent computations.
- `ret = (c[t] − c[t−1]) / c[t−1] × 100` per group; drop the first candle per
  group (no prior close).
- `range = (h − l) / l × 100`.
- Never pool timeframes in one histogram.
- If system pandas/matplotlib is missing: `uv venv .venv && uv pip install
  --python .venv/bin/python pandas matplotlib`.

## Command execution

- Python with a generous timeout (`timeout 600`), background + self-wake per
  fundamentals.
- Verify every deliverable exists and is non-trivial before `done.txt`.

## Self-command

```bash
( sleep 60; tmux send-keys -t 25-4 "Self-wake: check analysis progress. Files produced? errors? done?" Enter ) &
```

Window: `25-4`. On wake: check outputs, fix errors, iterate. When all six
deliverables exist, write `done.txt` with headline stats + the verdicts.
