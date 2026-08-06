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

## Results (20000 bars, budget 30k USDT, start 100k USDT)

| Regime | Return % | Max DD % | Fills | Commissions USDT | Profit factor |
|---|---|---|---|---|---|
| range | **+20.60** | -3.96 | 3373 | 3782.67 | 2.87 |
| trend (up) | -46.60 | -65.43 | 1839 | 1943.40 | 0.66 |
| downtrend | **-209.17** | -208.62 | 1572 | 1822.62 | 0.04 |
| mixed | -0.74 | -10.42 | 2572 | 2751.84 | 0.98 |

Note: the equity metric for downtrend goes negative (account blows up) because
the exposure cap is only enforced at rebalance, not on fills.

## Findings

- The implementation is **fee-efficient** per order: ~1600-3400 fills and
  ~1700-3800 USDT commissions per 3-month run. (The initial version churned
  19k fills and bled 20k USDT to fees before batched redistribution was
  introduced.)
- **The strategy has a real edge in ranging markets (+20.6%)** — the regime it
  is designed for — with a profit factor of 2.87 and modest drawdown.
- **It is destroyed by sustained trends**: +46% loss in a steady uptrend and
  a full blow-up (-235%) in a sustained downtrend. Fill accumulation between
  rebalances grows inventory past the exposure cap, and the opposite-side
  levels never fill in a one-directional market. This is the classic grid
  risk, made visible by the regime sweep.
- The volume-profile redistribution concentrates capital on one side over
  time; combined with a rebalance-only exposure cap, inventory control is
  insufficient in trends.

## Deliverables

- `interactive/sr-grid-explainer.html` — self-contained, offline, mobile-first
  teaching page. Animated candles with fractal pivots, the sliding 7-bar
  window, S/R levels, the ATR-spaced grid (line width = allocated capital),
  fills, rebalances, and the volume-profile KDE panel. Open it directly in a
  browser (no server needed).

## Next iterations (open questions)

- Enforce the exposure cap **on fill**, not only at rebalance (cancel the
  inventory side as fills approach the cap) — this is the highest-impact fix
  for the trend blow-ups.
- Add a **trend filter** to stop quoting the buy side (or go flat) during
  sustained downtrends.
- Test on **real data** (e.g. Binance BTC/USDT via Nautilus catalog) — synthetic
  Gaussian regimes are only a first pass.
- Vary grid span, level count, budget fraction, and rebalance interval in a
  parameter sweep.

## Inherits

- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — conventions,
  file-system orchestration, command rules
