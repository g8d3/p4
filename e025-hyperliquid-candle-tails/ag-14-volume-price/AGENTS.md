# ag-14 — Volume × price interaction for direction

Phase 6. The missing analysis: does **volume confirm or contradict price
moves**? Every prior volume feature predicted volatility (strongly) or
direction (flat). This tests the classic interaction hypothesis — "a move is
more likely to continue when volume supports it" — using the shared candles.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../ag-02-dist/AGENTS.md](../ag-02-dist/AGENTS.md) — derived columns
- [../ag-05-seasonality/AGENTS.md](../ag-05-seasonality/AGENTS.md) — split-sample + per-coin replication pattern
- [../ag-13-fees-filter/AGENTS.md](../ag-13-fees-filter/AGENTS.md) — the cost reality: most edges die at 0.09% round trip

Single agent, never downloads. Beginner-explain requirement applies.

## Inputs

- `../ag-01-data/output/candles_raw.csv` — `coin,tf,t_ms,o,h,l,c,v`. Drop v=0.
- Hyperliquid candles give TOTAL volume `v` per candle (no separate
  up/down-volume) — state that limitation. All signals below are computable
  from OHLCV.

## Primary timeframe: 1d

The fees filter (ag-13) showed intraday edges die at 0.09% round trip. This
is a daily/positional hypothesis. Analyze **1d primarily**, 1h as secondary
sensitivity only. Do not report 5m as tradeable evidence.

## Signals (the declared grid — all target DIRECTION)

For each signal, bucket and look at the **next 1-day and next 5-day return**
(mean, median, win rate) per bucket, per coin, split-sample:

1. **Move × volume interaction** — bucket by (sign of `ret[t]`, volume
   percentile of `v[t]` within its coin series). The classic test: up moves
   on high volume → continuation? up moves on low volume → reversal?
   Cross-bucket: is `E[ret_next | up, vol>90] ≠ E[ret_next | up, vol<50]`?
2. **OBV (On-Balance Volume)** — `OBV[t] = OBV[t−1] + sign(ret[t]) × v[t]`.
   Compute the OBV slope over a trailing window (e.g. 10 days) and its
   divergence from price slope. Buckets: OBV up & price up, OBV down & price
   up (bearish divergence), etc. → next-day return.
3. **VWAP distance** — `vwap_N = Σ(p_typ[t]×v[t]) / Σv[t]` over N=20, where
   `p_typ = (h+l+c)/3`. `dist = (c − vwap)/vwap` in σ units. Is price
   stretched above/below where volume traded → next-day return?
4. **Up/down volume ratio** — over trailing 10 candles: `Σv[up candles] /
   Σv[down candles]`. Bucket by ratio (predominantly up-volume vs
   down-volume) → next-day return.
5. **Volume-adjusted return** — `ret[t] / (v[t] / median_v)` (move per unit
   of relative volume). Does a move that happened on unusually low volume for
   its size behave differently going forward?

## Method & rigor

- All features from t and before; targets t+1 / t+5. No lookahead.
- **Split-sample**: first/second half by time per coin — replication required.
- **Per-coin replication rate**: effect must hold in a majority of coins.
- State the grid BEFORE running in session-log (no post-hoc features).
- If a signal is null → honest null. Expectation: these effects are real in
  the classic literature but small; most will not survive 0.09% costs. The
  point is to MEASURE, and to identify which interaction (if any) is strong
  enough on 1d to matter.

## Deliverables

| File | Contents |
|---|---|
| `output/signals.csv` | Per (signal, bucket, coin or pooled): n, mean/median next-1d and next-5d, split halves |
| `output/replication.csv` | Per (signal, tf): replication rate across coins + split-half consistency |
| `output/charts/*.png` | Bucket bars per signal, divergence illustration (~6) |
| `output/report.md` | Answers to the 5 signals, replication verdicts, net-of-fees note, honest nulls |
| `output/beginners_guide.md` | Volume confirmation, OBV, VWAP, divergence — for a beginner |
| `output/session-log.md` | Per e025 conventions |

## Pitfalls

- OBV and VWAP need a warm-up period; drop NaN/undefined early rows.
- Volume percentile must be per (coin, tf) — absolute levels differ wildly
  across coins.
- Sign of `ret[t]` for OBV uses close-to-close; state it.
- Don't present a single coin's bucket as a pattern; require replication.
- Fees reality: state the breakeven (0.09% RT) next to every effect size.

## Self-command

```bash
( sleep 60; tmux send-keys -t 25-14 "Self-wake: check progress. Files? errors? done?" Enter ) &
```

Window: `25-14`. Write `done.txt` with the 5 verdicts when done.
