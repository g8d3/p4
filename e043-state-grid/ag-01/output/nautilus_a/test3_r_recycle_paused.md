# Nautilus-A Test 3 — Feature 1: R-recycle (STATUS: paused, proof pending)

## What this document is

Status note written at 2026-08-25 night, before stopping. The machine is
quiet until a new session. Everything below is reproducible with the exact
commands in test1/test2 docs + the flags here.

## Hypothesis (from NAUTILUS_A_PLAN test 3)

"After a grid level fills on one side, freed capital re-enters only if price
retraces R% in the favourable direction (instead of the current immediate
redistribution). Capital re-enters only when the cycle is favourable ->
fewer stacked fills, less trend bleed."

## Interpretation 1 (my first read — WRONG for the goal): re-arm SAME side

Freed capital re-enters the SAME side after R% retrace. Result: **broken
machinery** (the sell side starves during trends; shops only buys). 5m:
−2.37% with only 77 fills (2,315 in the disabled stack). 1h: +15.34%, but
109 fills and PF 109 — a small-sample lottery per rule 5b, NOT evidence.
**Rejected as a reading** (does not keep the shop two-sided).

## Interpretation 2 (corrected): cycle-completion depth

Freed capital feeds the **opposite** side (as v2 does) but only after the
price moves R% in that side's favour (a sell after a buy-fill waits for a
+R% bounce). Results:

| Run | Return % | Max DD % | PF | Fills | Fees | n_positions | Win rate |
|---|---|---|---|---|---|---|---|
| 5m stack (no recycle) | +7.07 | −5.57 | 1.253 | 2,315 | 2,315.48 | — | — |
| 5m recycle R=0.5% | +5.84 | −4.82 | 1.21 | **78** | 186.75 | 313 | 71.6% |
| 5m recycle R=1.5% | −3.66 | −8.41 | 0.86 | **77** | 169.43 | 263 | 70.7% |
| 1h stack (no recycle) | +8.41 | −7.73 | 1.201 | 1,125 | 1,191.11 | — | — |
| 1h recycle R=0.5% | +3.20 | −7.80 | 1.07 | **110** | 255.65 | 232 | 65.5% |
| 1h recycle R=1.5% | +9.46 | −4.95 | 1.25 | **110** | 229.38 | 244 | 68.0% |

## The anomaly that BLOCKS the verdict

In ALL recycle runs the fill count collapsed (78-110 vs 1,125-2,315) and
fees dropped 10x. The 1h R=1.5% result (+9.46%, nicer DD) is likely a
low-activity artifact: the queue holds freed capital that is **not counted
in the rebalance budget** (`_rebalance_grid`: total_budget = grid_budget +
_unallocated + pending; the `_recycle_queue` amounts are invisible) so each
rebalance re-arms a progressively smaller grid; plus v2's
`on_order_rejected` does not refund `reserved` into `_unallocated` (a
pre-existing defect that never fired when freed capital flowed through
`pending`). Net effect: the machine idles small; nothing decided yet.

## Verdict — NOT YET, paused before proof

- Interpretation 1: **rejected** (mechanically one-sided).
- Interpretation 2: **evidence distorted** by the bookkeeping leak; cannot
  keep/reject. Suspected better on 1h (R=1.5), worse on 5m — unproven.

## WHAT FOLLOWS (next session, in order — none of it heavy work)

1. **Diagnostic run (INFO log, one 5m config):** count "Order rejected" and
   track budget/free-cash trajectory through the recycle runs. Expect
   rejection cascade as the queue grows.
2. **Fix the bookkeeping** in `sr_grid_strategy_user.py` (v2 untouched):
   a. Before/at rebalance: drain `_recycle_queue` into `_pending_redistribute`
      (amounts become visible to the budget) — wait, BUT that would defeat
      the retrace-wait; correct instead: add `sum(queue)` to total_budget and
      zero the queue when the amounts are recycled back into the grid
      (they re-enter the pool only when the retrace hits; the budget math
      already re-allocates them when queued — the queue is capital, it must
      appear in budget OR simply deposit queue amounts into `_unallocated`
      after each release and let rebalance do the rest).
   b. `on_order_rejected`: refund `lv.reserved` to `_unallocated`.
   c. Add `n_rejections` counter (metrics visibility).
3. **Re-run interpretation-2 A/B** R ∈ {0.5, 1.5} on both datasets (4 runs,
   ~1 min each), THEN the verdict. If 1h still shines, OOS 60/40 before any
   keep.
4. Continue Test 3 remaining features — each with its candidate card +
   pre-screen before the engine:
   - **Q multi-volume** (depth-scaled per-level capital): screen says it
     changes sizing, not signals → prior low as alpha (geometry only); test
     once, cheap.
   - **SL/V per-lot ladders**: pre-screen A/B says no band clears fees alone
     (50% real vs 56% needed at best) → prior low; but ladder OVER the grid
     (exits by its own target/stop) is different geometry from the flat
     (V,SL) screen — one A/B to see if any positive signal exists.
   - **State allocation targets** (side multipliers per regime from
     allocation_map): highest prior of the four (regime disarming already
     helped: test 2). Most promising of the remaining features.
5. Log every verdict in BASE_RATES.md + one plain-language lesson each.

## Commands used tonight

```bash
# interpretation 2, example (5m R=1.5%): add to the stack command from test2:
python3 e043-state-grid/ag-01/bin/run_backtest_user.py --strategy user \
  --data <5m> --out-dir output/nautilus_a/t3_recycle2_5m_r15 \
  --atr-mult 2.5 --max-levels 2 --min-order 1000 --trend-fast 50 --trend-slow 100 \
  --trend-enter 0.8 --trend-exit 0.5 --rebalance 192 \
  --flatten-mode limit_first --flatten-limit-offset-pct 0.05 --flatten-fallback-bars 3 \
  --recycle-enabled --recycle-pct 1.5
```
