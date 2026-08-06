# ag-01 — S/R grid strategy developer

Owns the strategy implementation, the synthetic-data generator, and the
backtest harness for experiment e022.

## Scope

Produce and validate:

1. `bin/sr_grid_strategy.py` — Nautilus Trader `Strategy` implementing the
   S/R grid with volume-profile redistribution (see
   [../AGENTS.md](../AGENTS.md) for the design).
2. `bin/gen_synthetic_data.py` — deterministic regime-switching OHLCV generator
   (mixed / range / trend / downtrend).
3. `bin/run_backtest.py` — BacktestEngine runner producing reports, metrics,
   and charts in `output/`.
4. `bin/run_sweep.sh` + `bin/summarize.py` — multi-regime comparison.
5. `output/` — generated artifacts (committed).

## Success criteria

- `python3 bin/run_backtest.py` runs end-to-end and writes all outputs.
- `bash bin/run_sweep.sh` completes all four regimes and writes `summary.csv`.
- Metrics are believable: fills and commissions must be modest (the grid must
  not churn); the results section in `../AGENTS.md` must match `summary.csv`.
- No hardcoded secrets; Python 3.12 + Nautilus 1.228 (pyo3 API).

## Environment / Model

- Default model: `opencode-go/deepseek-v4-flash` (cheap; sufficient for
  iteration). Use `opencode-go/mimo-v2.5` for vision review of charts.

## Commands

All long-running commands must be backgrounded with a self-wake, per
[../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md).

```bash
# generate data
timeout 60 python3 bin/gen_synthetic_data.py --mode mixed --n-bars 20000

# run a single backtest (~6s for 20k bars)
timeout 500 python3 bin/run_backtest.py

# full sweep (~1 min)
bash bin/run_sweep.sh

# summarize
timeout 30 python3 bin/summarize.py
```

## Pitfalls

- Nautilus 1.228 uses the **pyo3 API**: `BacktestEngine.add_venue/add_instrument/
  add_strategy/add_data` then `run()`. Reports are DataFrames on
  `engine.trader.generate_*_report(...)`; the account report needs
  `venue=Venue("SIM")`.
- Bar OHLC precision must match `instrument.price_precision` (2 for BTC).
- `cancel_order` and `cache.order` take an `Order` / `ClientOrderId` object,
  not a string; `Position.quantity.as_double()` has no `is_flat`/`is_zero`.
- `init_logging` panics if called twice; don't call it, pass `bypass=True` in
  `RiskEngineConfig` instead to disable order-submit rate limiting.
- Cancel+resubmit on every fill causes an order churn cascade (19k fills, 20k
  USDT commissions). Redistribute freed capital **once per bar** (pooled).
- A naive exposure cap alone makes the position whip between max-long and
  max-short; the cap must also be enforced on fills and combined with a trend
  filter to actually control inventory.
- A rebalance that is **skipped** (cap reached) must NOT be retried every bar:
  it runs `_detect_sr_levels` + numpy per bar (~19k times = +25s and log spam)
  and, worse, the old code re-added `grid_budget` to `_unallocated` on every
  skip, compounding the pool to ~292M USDT and corrupting results. Caps are
  checked before cancelling orders and attempts are throttled with
  `_last_rebalance_attempt`.
- Fractal pivots must compare against the **neighbours only** — including the
  bar itself in the window (`highs[i] >= np.max(highs[i-w:i+w+1])`) makes
  every bar a pivot (degenerate S/R). Compare `highs[i]` with the max of
  `[i-w:i]` and `[i+1:i+w+1]` separately.

## Self-command

Every command runs in background; after launching one, schedule a self-wake:

```bash
# generic self-wake pattern (replace window name and PID)
(sleep 120; tmux send-keys -t <window> "Self-wake: check PID=$PID / output files exist, diagnose and continue." Enter) &
```

Never block on a long command synchronously.

## Inherits

- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) —
  conventions, command execution rules, commit format
- [../AGENTS.md](../AGENTS.md) — experiment scope, design, results
