# ag-07 — Event study: what happens around 3σ moves?

Phase 4 of e025. Instead of studying every candle, isolate the **rare
events** (candles whose move exceeds ±3σ for their coin/timeframe), surround
each with a window, and study what is true BEFORE and AFTER them. Plus a new
feature: **how extended is price from its last confirmed swing high/low?**

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../ag-02-dist/AGENTS.md](../ag-02-dist/AGENTS.md) — derived column definitions
- [../ag-03-cond/AGENTS.md](../ag-03-cond/AGENTS.md) — honest-results + sample-size rules
- [../ag-05-seasonality/AGENTS.md](../ag-05-seasonality/AGENTS.md) — split-sample validation pattern

Single agent (A/B verdict). Reads the shared candles; **never downloads**.

## The beginner-explain requirement (absolute)

The user is a beginner. Every deliverable gets a "Plain English" section.
Explain in simple words: what an event study is, what 3σ means, what a
pivot/swing is, what no-lookahead means and why it matters, what MAE/MFE
mean. Include a `beginners_guide.md` tying it to the whole experiment.

## Input

`../ag-01-data/output/candles_raw.csv` — `coin,tf,t_ms,o,h,l,c,v`. Drop v=0
rows first. Compute per `(coin, tf)`, ordered by time:

```
ret    = (c[t] − c[t−1]) / c[t−1] × 100
range  = (h − l) / l × 100
body   = (c − l) / (h − l)             # 0 = close at low, 1 = close at high
sigma  = stdev(ret), per (coin,tf)     # global, for event detection
rolsig = rolling stdev(ret, 20)        # local regime (min 50 obs)
```

## Events

An **event** = candle with `|ret| > 3 × sigma` (both signs). Expect ~200–300
events per tf pooled, ~20–30 per coin. Do not split thinner than n≥50 per
subgroup.

## Swing-distance feature (confirmed pivots, NO LOOKAHEAD)

This is the user's requested column. Definition that never peeks at the
future:

- **Pivot high** at time t: `high[t]` is strictly greater than the highs of
  the N=5 candles before AND the N=5 candles after t. It is only *confirmed*
  at time `t+5`.
- **Pivot low** analog with lows.
- At any time t, the **last confirmed pivot high** is the most recent pivot
  whose confirmation time ≤ t (same for low).
- `dist_high = (close[t] − last_confirmed_pivot_high) / rolsig[t]`
- `dist_low  = (close[t] − last_confirmed_pivot_low)  / rolsig[t]`

Positive `dist_high` = price above its last swing high (extended up);
negative `dist_low` = price below its last swing low (extended down). Express
in σ units so coins/timeframes are comparable. Document this exact definition
in the deliverables — the no-lookahead property is the whole point.

## Questions (the declared grid — answer ALL, small by design)

1. **Momentum or reversion?** Average and median cumulative `ret` of the next
   1, 3, 5, 10 candles after an event. Up events and down events separately,
   per tf.
2. **Asymmetry?** Is the −3σ path the mirror of the +3σ path? Report both
   explicitly (crashes vs rallies often differ).
3. **Do events cluster?** Distribution of "candles until the next event" per
   coin/tf — are events closer together than random would predict?
4. **Does pre-event state change the reaction?** Split events by:
   a. swing extension at event time (`dist_high`/`dist_low` sign & magnitude)
   b. event candle volume percentile (high vs low)
   c. regime before event (`rolsig` high vs low)
   d. hour of day (only if n allows)
   Compare next-5-candle cumulative returns across the splits.
5. **Risk envelope**: max adverse excursion (MAE, worst drawdown within the
   next 10 candles from event close) and max favorable excursion (MFE).
   Report typical values (median, p90) per event side.
6. **Split-sample**: every path/pattern above must replicate on first-half vs
   second-half of the data (per coin, by time). No replication → noise.

## Deliverables

| File | Contents |
|---|---|
| `output/events.csv` | One row per event: coin, tf, time, side, ret, and ALL pre-event features + post-event outcomes |
| `output/event_paths.csv` | Average/median cumulative path (+1..+10) per (side, tf) and per split-half |
| `output/extension.csv` | The swing feature's own distribution + its relationship to events (do events occur more when extended?) |
| `output/charts/*.png` | Path curves up vs down per tf; MAE/MFE chart; event-interval histogram; extension×reaction plot. ~8 charts |
| `output/report.md` | Answers to the 6 questions with numbers, replication verdicts, honest nulls |
| `output/beginners_guide.md` | Event study + pivots + no-lookahead, for a beginner |
| `output/session-log.md` | Per e025 conventions |

## Honest expectations

- Volatility clustering is already proven: events WILL cluster and the
  path's width WILL be wider after events. That part is expected, not new.
- The genuinely NEW answers are about **direction and asymmetry**: does the
  full path revert or continue, and does the pre-event extension/volume
  state change it? Those may well be null — report them as null.
- With ~200–300 events per tf, only big effects will be visible. That is
  fine — it is what the data can support.

## Pitfalls

- Never let a "pre-event predictor" use candle data at or after the event.
- The pivot feature is undefined until the first confirmed pivot exists —
  drop those early rows or flag them.
- Global σ includes the fat tails, so a 3σ event is *unusual even for this
  fat-tailed coin* — that is the intended meaning.
- Correlated coins: pooled events are not 12× independent; say so in the
  report.

## Command execution

- Python + pandas + numpy + scipy + matplotlib (system-wide). Run
  backgrounded `timeout 600` + self-wake per fundamentals. Verify every
  deliverable exists before `done.txt`.

## Self-command

```bash
( sleep 60; tmux send-keys -t 25-7 "Self-wake: check progress. Files produced? errors? done?" Enter ) &
```

Window: `25-7`. On wake: check outputs, fix errors, iterate. When all
deliverables exist, write `done.txt` with the headline answers to the 6
questions.

## Notify (mandatory)
In addition to writing `done.txt`, agents MUST notify on completion:
`notify.sh done "<agent> finished: <headline>"` (from `../../e000-fundamentals/bin/notify.sh`)
On an unrecoverable failure, before giving up: `notify.sh error "<agent> failed: <cause>"`

