# e025 — Hyperliquid Candle Tail Analysis

**Goal**: detect statistical edges in Hyperliquid candles — the empirical
distribution of percentage moves, and whether extreme moves are *predictable*
from context (previous candle, volatility, volume).

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, data formats (CSV preferred)
- [../e021-hyperliquid-playground/AGENTS.md](../e021-hyperliquid-playground/AGENTS.md) — Hyperliquid API details, coin ranking, candle conventions

## Pipeline

Three agents, chained via the filesystem (AgentFS):

```
ag-01-data → output/candles_raw.csv  →  ag-02-dist → histograms + stats
                                    ↘  ag-03-cond → conditional tails + edge test
```

| Agent | Consumes | Produces |
|---|---|---|
| **ag-01-data** | Hyperliquid REST + e021 ranking | `output/candles_raw.csv`, `output/manifest.json` |
| **ag-02-dist** | `../ag-01/output/candles_raw.csv` | `output/stats.csv`, `output/hist_<tf>.csv`, `output/charts/*.png`, `output/report.md` |
| **ag-03-cond** | `../ag-01/output/candles_raw.csv` | `output/cond_next.csv`, `output/report.md` |

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
# ag-01 (data) — from this directory:
tmux new-window -n 25-1 -d
tmux send-keys -t 25-1 "cd ag-01-data && opencode" Enter
sleep 3
tmux send-keys -t 25-1 "Read AGENTS.md, then read each file listed in Inherits. Execute the task." Enter
```

Then ag-02 and ag-03 once `candles_raw.csv` exists (they read only ag-01's output, never ag-01's session).

## Conventions

- All outputs in the producer's `output/` directory; CSV for tabular data.
- Every command timed out; blocking commands backgrounded + self-wake.
- Results are descriptive first, inferential second. The experiment measures —
  it does not assume edges exist.
