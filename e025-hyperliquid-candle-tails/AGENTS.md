# e025 — Hyperliquid Candle Tail Analysis

**Goal**: detect statistical edges in Hyperliquid candles — the empirical
distribution of percentage moves, and whether extreme moves are *predictable*
from context (previous candle, volatility, volume).

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, data formats (CSV preferred)
- [../e021-hyperliquid-playground/AGENTS.md](../e021-hyperliquid-playground/AGENTS.md) — Hyperliquid API details, coin ranking, candle conventions

## Pipeline — A/B test: 3 agents vs 1 agent

The experiment doubles as a test of agent architecture. Both paths consume the
**same downloaded data** (ag-01 runs once; never download twice). They are
compared on wall-clock time, problems encountered, and output parity.

```
                    ┌─ Path A (3 agents) ─ ag-02-dist → ag-03-cond
ag-01-data (once) ──┤
    candles_raw.csv └─ Path B (1 agent) ── ag-04-monolith
```

| Agent | Consumes | Produces |
|---|---|---|
| **ag-01-data** (shared, runs once) | Hyperliquid REST + e021 ranking | `output/candles_raw.csv`, `output/manifest.json` |
| **ag-02-dist** (Path A) | `../ag-01-data/output/candles_raw.csv` | `output/stats.csv`, `output/hist_<tf>.csv`, `output/charts/*.png`, `output/report.md`, `output/session-log.md` |
| **ag-03-cond** (Path A) | `../ag-01-data/output/candles_raw.csv` | `output/cond_next.csv`, `output/report.md`, `output/session-log.md` |
| **ag-04-monolith** (Path B) | `../ag-01-data/output/candles_raw.csv` | ag-02 + ag-03 deliverables combined into ONE `output/`, plus `output/session-log.md` |

**Rules for the A/B test:**
- ag-01 runs once. Path B must NOT download — it reads the shared CSV.
- Both paths use identical output file names (`stats.csv`, `hist_<tf>.csv`,
  `cond_next.csv`) so parity can be checked with `diff`/`sha256sum`.
- Each analysis agent writes `session-log.md`: start/end timestamps, command
  count, every problem hit and how it was solved, anything that consumed
  context.
- After both paths finish, `comparison.md` (in this directory) is filled in by
  the orchestrator from the two session logs + output diffs.

## Scope (decided 2026-08-13)

- **Assets**: top-10 perps by notional volume AND open interest (union), from
  the e021 ranking.
- **Timeframes**: `5m`, `1h`, `1d`, `1w` (weekly replaces monthly — Hyperliquid
  is ~3 years old, monthly would have ~35 candles).
- **Candles per asset**: maximum available history (p99.9 tail quantiles need
  thousands of observations; 200 is too thin).

## Definition of done

- `candles_raw.csv` has ≥ 90% of the expected rows (per-coin, per-tf), zero
  duplicate `(coin, tf, t_ms)`, contiguous time coverage with a documented
  manifest of gaps.
- `stats.csv` gives per-`(coin, tf)` quantiles (p50/p90/p99/p99.9), skew,
  kurtosis, min/max — this is where fat tails are measured.
- `ag-03/report.md` states, for each signal tested, whether the next-candle
  tail shifts vs the unconditional distribution, with sample sizes — not
  vibes. Honest "no edge found" conclusions are valid results.

## Pitfalls

- **Never pool timeframes** in one histogram — 5m and 1w returns have
  incomparable scales. Always analyze per `tf` (or per z-score).
- **Integer division**: prices are decimal but treat ratios with `* 1.0`
  (SQLite/Python pitfalls).
- **candleSnapshot** returns max 5000 candles per request — paginate with
  `startTime = last_t + interval_ms`.
- Candle `t` is the **open** time in epoch ms; `endTime: 0` returns an error —
  always pass real millisecond times.
- Gaps: a missing candle can be a delisting or a trading pause. Note it in the
  manifest; don't silently treat it as a zero-move candle.

## Run

```bash
# ag-01 (data, ONCE — shared by both paths) — from this directory:
tmux new-window -n 25-1 -d
tmux send-keys -t 25-1 "cd ag-01-data && opencode" Enter
sleep 3
tmux send-keys -t 25-1 "Read AGENTS.md, then read each file listed in Inherits. Execute the task." Enter
```

Once `candles_raw.csv` exists, launch Path A and Path B:

```bash
# Path A — two windows (25-2 ag-02-dist, 25-3 ag-03-cond). ag-03 reads only
# ag-01's CSV, not ag-02's session — can run in parallel with ag-02 if desired.
# Path B — one window (25-4 ag-04-monolith).
```

Both paths write `session-log.md`; when both are done, the orchestrator fills
in `comparison.md` from the logs + `diff` of the outputs.

## Conventions

- All outputs in the producer's `output/` directory; CSV for tabular data.
- Every command timed out; blocking commands backgrounded + self-wake.
- Results are descriptive first, inferential second. The experiment measures —
  it does not assume edges exist.
