# e043 — Fase 2: Findings (honest) — base edge search exhausted

Date: 2026-08. Following the stopping rule agreed with the user ("stop at
edge-found or search-exhausted within a bounded budget"), Fase 2 searched for a
positive base edge to layer the ladder features on. **No in-house edge was
found.** This is the deliverable.

## What was tested

Option A (recommended): adopt e022's proven *two-sided ATR-spaced range grid*
(+3.6% 5m / +1.7% 1h) as the base, then layer the user's ladder features on it.

`ag-01/bin/range_grid.py` — standalone, Nautilus-free port of e022 v2
(SRGridStrategyV2): EMA fast/slow regime filter with hysteresis, ATR-spaced
levels around price, volume-profile capital allocation, freed-capital
redistribution to the opposite side, exposure cap + reduce-only flatten,
liquidation model, maker/taker fees. Indicators computed exactly like e022
(windowed cold-start EMA, ATR over last N incl. current).

## Evidence

**Sanity control — synthetic RANGE (should favor a grid, e022 v2: +13.8%):**

| Config | Return (fees ON) | Return (fees OFF) | Fills | Regime flips | FLAT fees |
|---|---|---|---|---|---|
| e0.3 lv2 | −1.53% | **+0.98%** | 791 | 639 | 1678 |
| e0.8 lv2 | +1.03% | **+2.54%** | 562 | 292 | 803 |

Mechanics verdict: the grid DOES make money gross on ideal range data, and the
quantified leak is **taker-flatten churn from regime flapping**: FLAT (taker)
fees are ~2× the GRID (maker) fees. This is a real, actionable design cost.

**Real BTC (bounded sweep, ~108 configs per TF):**

| Dataset | Best return | Notes |
|---|---|---|
| BTC 1h 4y | **−4.9%** (e0.3 lv2; fees-on value), −1.9% fees-off | cold-EMA artifact excluded |
| BTC 5m 1y | **−3.1%** (e0.8 lv2) | none positive |

After reducing the flatten churn (higher trend-enter threshold): 1h −7.6%,
5m −4.4%. Flat fees dropped to ~1/3 of commissions, but real-data results
stayed negative. **The e022-published base edge does not reproduce in a
simplified harness** — it lives only in their exact Nautilus engine (thin PF
1.04–1.14 even there).

> Note: an early sweep looked positive (+0.93% 1h) — that was an ARTIFACT of a
> cold-start EMA bug in the first sweep loop (first ~100 bars treated as RANGE,
> grid trading unprotected). With correct causal indicators it is negative.
> `range_sweep_1h.csv` from that buggy path was deleted; `range_sweep_5m.csv`
> used the corrected path.

## Verdict

Stopping rule reached: bounded search (~200 ladder configs in Fase 1, ~216
range-grid configs in Fase 2) exhausted without a robust positive edge in this
harness. Two honest conclusions:

1. **The one-sided %-ladder (user's original design) is structurally negative**
   in Fase 1 — bottleneck is entry win rate (~20–42%), not tuning.
2. **The two-sided range grid family is real but thin and execution-sensitive:**
   it needs e022's exact Nautilus engine (proper fill/venue simulation) to show
   its +1.7%/+3.6%; my simplified port can't validate it. And a quantified
   design leak exists that the user's state layer could attack: **taker-flatten
   churn from regime flapping** (2× the maker fees).

## Recommendation (evidence-based)

- **Do not trust this simplified harness as the final judge** of thin-grid edges;
  use it as a fast hypothesis filter only.
- **To layer the user's ladder features (R-recycle, multi-volume Q, multi-stop
  SL/V, state allocation targets) on a positive base, run them inside e022's
  ACTUAL Nautilus harness** (`../e022-nautilus-sr-grid/ag-01/bin/run_backtest.py
  --strategy v2`), which is the only place the base edge demonstrably exists.
  The features become Nautilus strategy additions; A/B each against v2's
  +3.6%/+1.7% baseline.
- **Two design levers worth testing there** (quantified here): reduce regime
  flapping (higher enter threshold / longer EMA) and flatten with maker limit
  orders instead of taker markets.
- Option B (improve the ENTRY, keep the ladder) remains untested; it targets the
  actual bottleneck (win rate) but needs its own bounded A/B campaign.

## Files

- `ag-01/bin/range_grid.py` — two-sided ATR range grid (port, standalone)
- `ag-01/bin/run_grid.py` — driver with exact-e022 indicators (precomputed)
- `ag-01/bin/sweep_grid.py` — base sweep (corrected causal path)
- `output/range_sweep_5m.csv`, `output/rg_1h/metrics.json`, `output/rg_5m/metrics.json`
- `output/FASE1_FINDINGS.md` — the one-sided ladder failure (structural)