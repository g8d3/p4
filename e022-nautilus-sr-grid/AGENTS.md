# e022 — Nautilus S/R Grid Strategy

Experiment to build and backtest a **grid trading strategy on Nautilus Trader**
where grid levels are placed automatically on support/resistance levels and
capital freed by filled grid orders is re-distributed to the opposite side
according to a **volume-profile probability distribution**.

## Goal

Build a faithful, testable Nautilus implementation of this strategy and run a
backtest harness on synthetic market data across different market regimes to
understand where it makes and loses money.

## Strategy

`ag-01/bin/sr_grid_strategy.py` — `SRGridStrategy`:

1. **S/R level detection**: fractal pivots (window `pivot_window`), filtered to
   the last `pivot_lookback_bars`, clustered into levels within
   `cluster_tol_pct`. Grid levels are selected around the current price within
   `grid_span_pct` and gap-filled at ATR spacing when S/R levels are sparse.
2. **Budget allocation**: on each rebalance (every `rebalance_interval_bars`),
   the grid budget is split across sides proportionally to the number of levels
   on each side; within a side it is allocated proportional to a **volume
   profile distribution** (KDE of traded volume over a rolling window).
3. **Fill redistribution**: when a grid order fills, the capital reserved for
   that order is freed and moved to the **opposite side**, distributed across
   that side's levels by the volume-profile probabilities. Applied once per bar
   to avoid order churn.
4. **Risk**: `max_exposure_budget_mult` caps net position notional. When a
   rebalance would push exposure past the cap, the side that adds inventory in
   the capped direction is not quoted.

## How to run

```bash
# 1. Generate synthetic data (default: mixed regime, 20k 5-min bars)
python3 ag-01/bin/gen_synthetic_data.py --mode mixed --n-bars 20000

# 2. Run one backtest (~6s for 20k bars)
python3 ag-01/bin/run_backtest.py

# 3. Sweep across all regimes (range / trend / downtrend / mixed)  (~1 min)
bash ag-01/bin/run_sweep.sh

# 4. Regenerate the comparison summary
python3 ag-01/bin/summarize.py
```

Requires `nautilus-trader` >= 1.228 (pyo3 API), `pandas`, `numpy`, `matplotlib`.

## Outputs (ag-01/output/)

| File | Producer | Contents |
|---|---|---|
| `summary.csv` | `summarize.py` | Per-regime comparison table |
| `<mode>/metrics.json` | `run_backtest.py` | Performance metrics per regime |
| `<mode>/equity_curve.csv` | `run_backtest.py` | Equity curve samples |
| `<mode>/equity_curve.png` | `run_backtest.py` | Equity + price chart |
| `<mode>/account_report.csv` | `run_backtest.py` | Nautilus account report |
| `<mode>/fills_report.csv` | `run_backtest.py` | Nautilus fills report |
| `<mode>/positions_report.csv` | `run_backtest.py` | Nautilus positions report |
| `data/synthetic_5m_<mode>.csv` | `gen_synthetic_data.py` | Synthetic OHLCV input |

## Real data reality check (the truth)

The synthetic "robust config" **does not transfer to real markets**. Results on
real BTC/USDT klines (Binance), start 100k USDT:

| Dataset | Config | Return % | Max DD % | Fills | Commissions |
|---|---|---|---|---|---|
| BTC 5m, 1 year | robust (span 3.5, lev 6, reb 96, cap 10x) | **-20.6** | -48.5 | 13,424 | 25,235 |
| BTC 5m, 1 year | defaults | -30.2 | -30.3 | 16,181 | 20,654 |
| BTC 1h, 4 years | robust | -79.4 | -94.3 | 6,918 | 7,183 |

Two distinct killers:
1. **5m is fee-dominated**: 13-16k fills/year bleed 20-25% of capital to maker
   fees. Real 5-min BTC crosses grid levels far more than smooth synthetic data.
2. **1h is trend-dominated**: over 4 years (2022 bear, 2023-24 bull) the grid
   accumulates inventory into trends and the counter-trend side never fills.

**Conclusion**: the +50% synthetic "edge" was an artifact of Gaussian regime
structure, not a real market edge. This is the single most important result of
the experiment — it is exactly why out-of-sample real validation is mandatory
and why "profitable in backtest" on synthetic data means almost nothing.

`data/real_btc_5m.csv` (105k bars, 1y) and `data/real_btc_1h.csv` (35k bars,
4y) are the inputs; `output/real_*` hold the reports.

## Baseline results (original defaults, 20k bars, budget 30k, start 100k)

| Regime | Return % | Max DD % | Fills | Commissions USDT | Profit factor |
|---|---|---|---|---|---|
| range | +20.60 | -3.96 | 3373 | 3782.67 | 2.87 |
| trend (up) | -46.60 | -65.43 | 1839 | 1943.40 | 0.66 |
| downtrend | -209.17 | -208.62 | 1572 | 1822.62 | 0.04 |
| mixed | -0.74 | -10.42 | 2572 | 2751.84 | 0.98 |

Note: the -209% downtrend used the ORIGINAL generator, whose unbounded drift
collapsed the price to ~1 USDT/BTC (-99.99%). The generator is now bounded
(floor/cap), so that blow-up was largely a data artifact. The defaults also
changed since (pool clamp, fill-time cap, trend filter added) — see below.

## Optimization (parameter search + out-of-sample validation, SYNTHETIC ONLY)

`ag-01/bin/optimize.py` grid-searches the strategy across 486 configs on the
range + mixed synthetic regimes (the hard ones) and validates the top ones
out-of-sample on 3 unseen synthetic seeds × 4 regimes. Search space: grid span
{1.0, 2.0, 3.5}, max levels {4, 6, 8}, rebalance {48, 96, 192}, exposure cap
mult {3, 6, 10}, trend filter {off, on}, trend min-dist {1, 2, 3}%.

> **IMPORTANT**: everything in this section is synthetic-only. The real-data
> reality check above shows the results do NOT carry over to real BTC.

### Robust (recommended) configuration

| Param | Value |
|---|---|
| `grid_span_pct` | **3.5** |
| `max_levels_per_side` | **6** |
| `rebalance_interval_bars` | **96** |
| `max_exposure_budget_mult` | **10** (loose — see caveat) |
| `trend_filter_enabled` | False |

Training mixed: **+50.1%** / -10.0% DD. Out-of-sample (3 unseen seeds):

| Regime | Mean | Min | Max |
|---|---|---|---|
| range | +16.1% | +13.5% | +17.8% |
| mixed | **+23.8%** | +5.8% | +43.7% |
| trend (up) | +30.3% | +5.3% | +46.8% |
| downtrend | +45.6% | +12.8% | +62.2% |

Run it with: `python3 ag-01/bin/run_backtest.py --span 3.5 --max-levels 6
--rebalance 96 --max-exposure-mult 10`

### The search also caught an overfit

The config that scored best on training data (span 3.5, levels 6,
**rebalance 48**, cap 10x — +54.8%) **fails out-of-sample**: mixed mean -1.9%,
one seed -50.5%. The only difference vs the robust config is the rebalance
interval (48 vs 96): rebalancing too often overfits the training noise. This is
why the out-of-sample step is mandatory, not optional.

### Caveats

- **Very high exposure**: the robust config reaches ~314k USDT notional on a
  100k account (~3.1x leverage). In the sim (margin_init=0, no liquidation) this
  is free; on a real exchange it means margin/liquidation risk. This is
  synthetic data — treat these numbers as a strategy test, not a forecast.
- The "trend fade" edge comes from quoting only the counter-trend side in
  sustained synthetic trends, which are cleaner than real markets.

## Operational lessons (from running the search on a 6-core laptop)

- **BLAS oversubscription**: 8 parallel workers × OpenBLAS (all cores each) =
  96 threads on 12 → the machine froze. `optimize.py` forces
  `OPENBLAS_NUM_THREADS=1` etc. per process and caps workers.
- **Nautilus memory leak**: each backtest run leaks ~25MB of Rust/pyo3 memory.
  Recycled workers (`max_tasks_per_child=10`) keep it bounded; without it, one
  worker reached ~3GB and the OOM killer killed the search (and earlier, froze
  the machine with 8 workers).
- **Transient hangs**: ~1 in every ~50 runs Nautilus hangs (worker stuck in a
  futex, no CPU). Root cause not yet pinned down (transient; `faulthandler`
  armed but the affected runs were clean). The harness is built to survive it:
  incremental CSV + resume + chunked execution with a watchdog that isolates
  stuck tasks. To nail the root cause, run a long series with `faulthandler`
  until a hang dumps its stack.

## Findings

- The implementation is **fee-efficient** per order: ~1600-3400 fills and
  ~1700-3800 USDT commissions per 3-month run.
- **The grid's edge comes from holding inventory**: tight exposure caps (1.5x
  budget) strangle the mean-reversion (mixed goes negative); loose caps (10x)
  + wide span make it robustly profitable across all synthetic regimes
  (see Optimization). The cap is a risk dial, not a free lunch.
- **Out-of-sample validation is essential**: the best training config overfit;
  only the OOS step separated the robust config from the overfit one.
- The volume-profile redistribution + ATR gap-filling are what place sensible
  levels; parameter sensitivity is dominated by grid span, rebalance interval,
  level count, and exposure cap.

## Deliverables

- `interactive/sr-grid-explainer.html` — self-contained, offline, mobile-first
  teaching page. Animated candles with fractal pivots, the sliding 7-bar
  window, S/R levels, the ATR-spaced grid (line width = allocated capital),
  fills, rebalances, and the volume-profile KDE panel. Open it directly in a
  browser (no server needed).

## Next iterations (open questions)

- **The strategy, as designed, does not make money on real BTC** (see real-data
  check). To have any chance it needs a redesign, not more tuning:
  - Cut churn (the 5m killer): much wider level spacing, higher
    `min_order_notional`, maker-only, or fewer, more selective levels.
  - Trend protection (the 1h killer): a strong trend filter or a regime switch
    that goes flat in trends instead of quoting one side.
  - Realistic fees (taker 0.04-0.10%, not 0.02% maker everywhere) and a
    liquidation/leverage model.
- **Nail the Nautilus hang root cause**: run a long config series with
  `faulthandler` armed until a hang dumps its stack; it is transient (~1/50
  runs) and currently only survived via the watchdog + resume machinery.
- Re-run the search on **out-of-sample data only** (proper train/test split) if
  the strategy is redesigned.

## Inherits

- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — conventions,
  file-system orchestration, command rules
