# e043 — Nautilus-A: plan (test the user's features on e022's real harness)

Decision taken with the user (2026-08): proceed with A — layer the user's
features onto e022's *actual* Nautilus harness (`SRGridStrategyV2`), because it
is the only judge where the thin base edge demonstrably exists
(+3.6% 5m / +1.7% 1h, PF 1.04–1.14).

Protocol = **copy-then-improve**: baseline untouched, ONE change at a time,
out-of-sample validation per change, keep only improvements. No blind sweeps.

## Baseline to beat (e022 v2, after fees, start 100k)

| Dataset | Config | Return | Max DD | Fills | Commissions | PF |
|---|---|---|---|---|---|---|
| BTC 5m 1y | atr 2.5, lv 2, reb 192, trend 50/100 | +3.65% | −7.16% | 2,158 | 2,393 | 1.14 |
| BTC 1h 4y | reb 96, cap 4×, trend 20/100 | +1.71% | −7.55% | 1,103 | 1,975 | 1.04 |

Data: `../e022-nautilus-sr-grid/ag-01/data/real_btc_5m.csv`, `real_btc_1h.csv`.
Run: `../e022-nautilus-sr-grid/ag-01/bin/run_backtest.py --strategy v2 ...`
(CLI knobs: `--atr-mult --max-levels --min-order --trend-fast/slow/enter/exit
--rebalance --max-exposure-mult`).

## How each test is run

1. Reproduce the baseline numbers on both datasets (report parity vs the table).
2. Add the change behind a config flag on a NEW strategy file
   (`sr_grid_strategy_user.py`, inherits V2 mechanics; v2 file untouched).
3. A/B change-on vs change-off, same grid, same data.
4. OOS sanity: re-run the winner on the 60/40 split (first 60% train / last 40%
   test) — same discipline as e022's `optimize_v2_oos`.
5. Keep only if it improves PF or return with DD not worse; else document why.

## Test 1 — flatten with maker limit instead of taker market (quantified leak)

From Fase 2: taker-flatten churn from regime flapping was ~2× the grid maker
fees on synthetic range (FLAT fees 1,678 vs GRID 837 on 30k budget). When a
trend is declared the flatten currently uses a reduce-only MARKET order. Change:
try a reduce-only LIMIT at the far grid level (or the current price ± small
buffer) first; fall back to market after N bars. Hypothesis: less taker bleed,
same protection. Accept if: commissions ↓ by >10% and return not worse.

## Test 2 — weather check stricter (enter threshold)

Fase 2 showed the regime filter is the dominant control; e022's own 5m headline
used trend 50/100. Test enter_pct ∈ {0.3, 0.8} vs baseline {0.5} on both
datasets (keep hysteresis exit at 0.2). Accept if: return improves with DD not
worse (this is a thin-edge family — small wins count).

## Test 3 — the user's features on the grid (the reason for this experiment)

Layer ONE at a time, each behind a flag:

| Feature | What it does | Hypothesis |
|---|---|---|
| **R-recycle depth** | After a grid level fills on one side, freed capital re-enters on the SAME side only if price retraces R% below/above the fill (instead of the current immediate same-side redistribution) | Capital re-enters only when the cycle is favorable → fewer stacked fills, less trend bleed |
| **Q multi-volume** | Per-level capital: `equal` (v2 has volume-profile KDE) vs `depth_scaled` (more capital on deeper levels) | Depth-weighted averaging is gentler in trends |
| **SL/V per-lot ladders** | Each grid level carries its own take-profit and stop (V/SL % ladders) so a filled level exits on its own target/stop instead of only via opposite-side levels | Bounded per-lot risk and time-in-inventory |
| **State allocation targets** | Side multipliers per regime from `allocation_map` (e.g. long disabled when TREND_DOWN even before full flatten) | Extra inventory control during early trends |

Each feature: on/off A/B, then OOS, then combine survivors. Success/fail
recorded per feature in `ag-01/output/nautilus_a/`.

## Deliverables

- `../e022-nautilus-sr-grid/ag-01/bin/sr_grid_strategy_user.py` (the layered
  strategy; v2 untouched)
- Per-test results in `e043-state-grid/ag-01/output/nautilus_a/` (metrics
  tables + plain-language verdicts for the course)
- One lesson per test added to `COURSE_NOTES.md` ("how to run a disciplined A/B")

## Guardrails

- Machine is shared/quiet: run tests one at a time, cap Nautilus workers.
- Every run timeout-wrapped; kill by PID.
- Commit after each meaningful step; notify on completion/failure.