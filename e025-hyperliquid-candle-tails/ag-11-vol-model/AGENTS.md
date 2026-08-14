# ag-11 — Volatility model: GARCH + EVT for sizing

Phase 5d. Convert "volatility clusters" (proven in ag-03/05/07) into a usable
forecast: model the next-candle volatility and the probability of extreme
moves, then turn it into position-sizing inputs.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../ag-02-dist/AGENTS.md](../ag-02-dist/AGENTS.md) — derived columns

Single agent, never downloads. Beginner-explain requirement applies (GARCH and
EVT explained for a beginner in Plain English).

## Inputs

- `../ag-01-data/output/candles_raw.csv` — candles (drop v=0 rows).
- Work on **1h** primarily (longest clean intraday series, ~5000 obs/coin) and
  1d secondarily.

## Method

1. **GARCH/EGARCH(1,1)**: fit per coin on 1h `ret`. Forecast next-candle σ.
   Evaluate honestly: correlation of forecast vs realized |ret|, and whether
   the forecast beats the simple empirical features already proven (volume
   percentile, cooloff, hour) in a head-to-head comparison.
2. **EVT on the tails** (peaks-over-threshold / generalized Pareto):
   estimate P(|ret| > x) per coin, per tf. Report the tail quantiles the
   empirical data can't reach (e.g. P(|ret| > 10σ)).
3. **Sizing table**: given the model state (forecast σ vs its own history),
   produce a practical table — "if forecast vol is at percentile P, suggested
   risk-per-trade multiplier is X" (fixed-fractional scaling, e.g. risk 1% of
   capital scaled inversely to vol). This is the bridge from statistics to
   position sizing. Label it as an illustration, not advice.
4. Compare with the empirical vol buckets from ag-05: is GARCH meaningfully
   better, or is the simple bucket rule just as good? (Cheaper is better.)

## Deliverables

| File | Contents |
|---|---|
| `output/vol_forecast.csv` | Per (coin, tf): model σ forecast vs realized |ret|, next candle |
| `output/evt_tails.csv` | Per (coin, tf): GPD tail fit params + extreme quantiles |
| `output/head_to_head.csv` | GARCH forecast vs vol_pct/cooloff buckets — which predicts better |
| `output/charts/*.png` | Vol forecast vs realized scatter; tail fit plot; sizing curve (~5) |
| `output/report.md` | Findings, which method wins, sizing table, honest limitations |
| `output/beginners_guide.md` | What GARCH and EVT are, why sizing matters, for a beginner |
| `output/session-log.md` | Per e025 conventions |

## Pitfalls

- Fit GARCH on stationary returns; use `arch` or `statsmodels` if available
  (`pip install arch` via uv venv if missing — see e000 venv pattern).
- Don't overfit: GARCH(1,1) is the standard; no fancier variants unless a
  clear win is shown.
- EVT needs enough tail samples; state n per fit; thin tails (1w) → skip with
  a note.
- Walk-forward the model evaluation: fit on first half, evaluate on second.

## Self-command

```bash
( sleep 60; tmux send-keys -t 25-11 "Self-wake: check progress. Files? errors? done?" Enter ) &
```

Window: `25-11`. Write `done.txt` with the verdicts when done.

## Notify (mandatory)
In addition to writing `done.txt`, agents MUST notify on completion:
`notify.sh done "<agent> finished: <headline>"` (from `../../e000-fundamentals/bin/notify.sh`)
On an unrecoverable failure, before giving up: `notify.sh error "<agent> failed: <cause>"`

