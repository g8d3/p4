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

## Redesign phase (v2): make the grid survive real BTC

Phase 1 (v1, `sr_grid_strategy.py`) proved the grid does NOT make money on real
BTC: -20.6% on 5m 1y (fee-dominated, 13-16k fills) and -79.4% on 1h 4y
(trend-dominated inventory). Phase 2 must **redesign the strategy**, not tune it.

### Hard constraints

- **Do NOT modify `sr_grid_strategy.py`** — it stays as the committed v1
  baseline. Write the new strategy in a NEW file `bin/sr_grid_strategy_v2.py`
  (class `SRGridStrategyV2`), keeping the same constructor/interface so
  `run_backtest.py` works unchanged. Add a `--strategy v2` flag to
  `run_backtest.py` if needed.
- Reuse `run_backtest.py`, `fetch_binance.py`, and the real CSVs in `data/`.
- Success criteria (same harness, start 100k USDT, after fees):
  - `real_btc_1h.csv` (4y) and `real_btc_5m.csv` (1y) must be **profitable or
    near-zero with realistic fees** (maker 0.02%, taker 0.06% — not 0.02% on
    both sides). Fills must drop well below v1 (target < 3k on 5m 1y).
  - Synthetic data is only for A/B sanity; the verdict comes from real BTC.

### The two killers to attack

1. **5m churn / fees**: price-space the grid (min gap between levels >= ~1.5x
   ATR), far fewer levels (2-3 per side), higher `min_order_notional`,
   maker-only quoting.
2. **1h trend inventory**: replace "quote the counter-trend side" with a
   **flat regime switch** — when a trend filter (EMA slope / ADX-style) is
   strong, cancel the grid and hold zero position; re-arm on reversion.
3. Add a simple **liquidation / leverage model** (margin + liquidation price)
   so the ~3x effective leverage of v1 is honest in the sim.

Report per-run metrics against the v1 baseline (see `../AGENTS.md` real-data
table) and update `../AGENTS.md` with the v2 outcome.

### v2 outcome — DONE

`bin/sr_grid_strategy_v2.py` (`SRGridStrategyV2`) is implemented and both
killers are defeated on real BTC (see `../AGENTS.md` for the full table):
5m 1y -20.6% → **+3.6%** (13,424 → 2,158 fills), 1h 4y -79.4% → **+1.7%**
(6,918 → 1,103 fills), realistic maker 0.02% / taker 0.06% fees, ~98% maker
fills. Run it with `python3 bin/run_backtest.py --strategy v2 --data
data/real_btc_5m.csv [--out-dir output/v2_5m]`. Config knobs are CLI-exposed:
`--atr-mult`, `--max-levels`, `--min-order`, `--trend-fast/slow/enter/exit`,
`--trend-off`, `--rebalance`, `--max-exposure-mult`. `bin/sweep_v2.py` sweeps
configs and writes `output/v2_sweep_*.csv`.

New pitfalls learned this phase:

- **The exposure cap must REDUCE the position, not just cancel orders**: v1's
  cap cancelled the inventory side but the position kept riding to ~2.3x
  account notional. `_enforce_cap_on_fills` in v2 flattens the over-cap excess
  with a reduce-only market order (inside a `cap_overshoot_pct` band so it
  doesn't re-fire every bar).
- **The 5m rebalance interval is a sharp ridge**: reb 160 = +8.4%, reb 176 =
  -5.6%, reb 192 = +3.6%, reb 208 = -7.8%. The exact value matters far more on
  5m than 1h. Prefer reb 192 (long anchoring avoids v1's "walk-up" where buys
  fill and sells get re-centred away, leaving permanent long inventory).
- **The flat regime switch needs hysteresis**: enter 1.0% / exit 0.5% on EMA
  50/100 (fewer flips than 0.5/0.2, which flapped ~800+ times on 5m and
  churned flatten taker fees).
- **`opencode run -f <file> "message"` parsing**: the message must come BEFORE
  the `-f` flags, otherwise `-f` swallows the message as a filename.
- **The Nautilus hang (~1/50) did NOT reproduce in 478 runs** across three
  dedicated harnesses (`hang_catcher.py`, `hang_catcher_parallel.py`, and an
  exact replica of the original 8-worker unrestricted-BLAS condition) with
  `faulthandler.dump_traceback_later(exit=True)` armed. Conclusion: it was
  machine-state-dependent, not a deterministic strategy/harness bug.
- **Root cause (probably) — fork after importing Nautilus/jemalloc**: building
  a parallel worker pool (`ProcessPoolExecutor`) whose parent has already
  imported Nautilus reproduces the hang deterministically: the parent spawns
  a `jemalloc_bg_thd` background thread, and forking a process with an active
  jemalloc bg thread deadlocks the child in `futex_wait` at first allocation.
  Evidence: (a) `optimize_v2_oos.py` hung at pool startup when the parent
  imported Nautilus (via `run_backtest`/`sr_grid_strategy_v2`); (b) passing
  pickled pyo3 Bars to workers also hung; (c) fixing the parent to NEVER
  import Nautilus (workers load it fresh in their own process) made the pool
  run clean. `optimize_v2_oos.py` therefore runs each config as a SEPARATE
  `subprocess` of `run_backtest.py` (the same model as `sweep_v2.py` and the
  hang catchers, which never hung in 478 runs). Do NOT reintroduce a
  ProcessPoolExecutor whose parent imports Nautilus.
- **Trend-following overlay prototype (`bin/trend_follow.py`)** — the upgrade
  of v2's flat regime switch: CAPTURE trends instead of going flat. On real 1h
  4y, EMA 100/400 with enter 1.0%/exit 0.5% at 2× budget gives **+37.7%** (DD
  -24.1%, PF 1.23) vs grid-only +1.7%; on 5m the same config loses (-12.5%).
  Confirms dual-regime: grid in range, trend-follow in 1h trends. Needs risk
  budgeting between modes before combining (trend DD is 2-3× the grid's).

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
