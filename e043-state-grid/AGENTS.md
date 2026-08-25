# e043 — State Grid

Experiment to design and backtest a **percentage-ladder grid** — a "special
grid" where buy, sell (take-profit), rebuy, and stop-loss depths are each a
*ladder* (a distribution) of percentages, under a **portfolio-allocation
target layer** whose setpoints change with **state** (measured market
variables, not calendar time).

## Status

- **Fase 0 — SPEC (in progress):** the full design living in [SPEC.md](SPEC.md).
  This is the current deliverable. The user is resolving the remaining open
  decisions (marked `TODO` in the SPEC).
- **Fase 1 — Backtest (next):** bar-by-bar event-driven simulation on real BTC,
  benchmarked against e022's post-fee results. Not started.
- **Fase 2 — Adaptive mappings (later):** one state→parameter mapping at a time,
  A/B against the static version, out-of-sample validated.

## What makes this different from a plain grid

- **Four ladders, not three:** `C` (buy depth), `V` (take-profit), `R` (rebuy
  after a sell), and `SL` (stop-loss) — plus `Q`, the capital distribution
  across levels. Each level is a lot with its own (volume, stop, target) triple.
- **Long + short mirror:** the whole ladder set is mirrored on the short side.
- **State-dependent allocation targets:** the strategy's "success" is defined as
  tracking a target portfolio allocation that changes with market state. The
  grid is the *controller* that moves the portfolio toward the setpoint. This
  gives a natural inventory bound (solves "I buy and can't sell").
- **Dynamic trailing stop:** trailing distance is a parameter, optionally
  volatility-scaled (`trail_dist_mode = atr_mult`) — distance breaths with
  volatility (chandelier-style).
- **Three-tier parameters:** structural (decide by design), ladder shapes (sweep
  2-3 at a time), adaptive mappings (one at a time, A/B). This discipline exists
  because of the overfit caught in e022.

## Key lessons inherited from e022 (must not repeat)

- **Fee drag kills short-TF grids:** e022's 5m grid did 13,424 fills/yr →
  −20.6% (~25k USDT fees on 100k). Breakeven rule: every take-profit must clear
  2×(maker fee + slippage).
- **Inventory accumulation kills trend grids:** buy-and-can't-sell. The ladder
  depth IS max exposure — bound it, and disarm in trends.
- **Best training config overfit** (+54.8% train → −1.9% OOS). Out-of-sample
  validation is mandatory, not optional.
- Real-market benchmark to beat: e022 v2 after fees = **+3.6% (5m 1y)**,
  **+1.7% (1h 4y)**, with max DD below ~8%.

## Data sources (available)

- `../e022-nautilus-sr-grid/ag-01/data/real_btc_5m.csv` — 105k bars, 1y
- `../e022-nautilus-sr-grid/ag-01/data/real_btc_1h.csv` — 35k bars, 4y
- Live feeds via `../e021-hyperliquid-playground/` (book walls/imbalance queries
  can weight `Q` by market liquidity in a later phase).

## Design principles

- **State, not time:** any adaptive parameter is a *function of measured market
  variables* (ATR, EMA slope, spread), never of the calendar. State must be
  causal (past bars only, no lookahead).
- **Lot-based exits:** "multiple stop losses at one price with different
  volumes" is implemented by pre-splitting the entry into lots with distinct
  (volume, stop, target) — the SL/V/Q ladders. No fractional-exit machinery.
- **Everything is a parameter in the framework, but few are swept at once**
  (three-tier rule).

## How to run

Fase 1 (not yet built). When the SPEC TODOs are resolved, implement a
bar-by-bar event-driven simulator (single Python process, no Nautilus needed —
simpler and sufficient for this) that:

1. Reads real BTC OHLCV CSV.
2. Walks bars causally; per bar, computes state (from past bars only).
3. Resolves allocation target for the state; places/cancels ladder orders to
   move the portfolio toward it.
4. Simulates fills at close (or on intrabar touch if added later), maker/taker
   fees, trailing-stop updates on new peaks.
5. Emits fills/positions PnL + the five success metrics.

Benchmark against the e022 numbers above. Then Fase 2 adds one mapping at a time.

## Conventions

- All files, code, and responses in English (user dictates in Spanish).
- Follow [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md):
  command timeouts, background + self-wake, kill by PID, quiet window
  (21:00–10:00), notify on completion/failure, commit after each change.
- CSVs preferred for tabular data; JSON only for non-tabular metadata.

## Deliverables

| File | Producer | Contents |
|---|---|---|
| `SPEC.md` | orchestrator/design | The full parameterized design (current deliverable) |
| `ag-01/bin/sim.py` | Fase 1 | Bar-by-bar backtest engine (`sim.py --data <csv> --config <json>`) |
| `ag-01/bin/sweep.py` | Fase 1 | Tier-2 parameter sweep |
| `ag-01/output/*` | Fase 1+ | Summary CSV, equity curve, fills report, metrics.json |

## Inherits
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — conventions, command rules, data formats
- [../e022-nautilus-sr-grid/AGENTS.md](../e022-nautilus-sr-grid/AGENTS.md) — the reality check and the edge to beat
