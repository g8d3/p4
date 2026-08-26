# Nautilus-A Test 3 — Feature 1: R-recycle (VERDICT, 2026-08-26)

Supersedes `test3_r_recycle_paused.md`. Reproducible with the stack commands
at the bottom of this doc.

## Hypothesis (test 3 feature 1)

"After a grid level fills on one side, freed capital re-enters only if price
retraces R% in the favourable direction (instead of the current immediate
redistribution). Capital re-enters only when the cycle is favourable -> fewer
stacked fills, less trend bleed."

## What we thought (night of 08-25) vs what we found

| Claim (paused doc) | Actual (this session) |
|---|---|
| fills collapse 2,315 -> 78-110 in ALL recycle runs | **False**: fills_report rows were normal (2,096 / 1,142 / 1,060). The 78-110 numbers were `strategy.n_fills` + `total_commissions` DISPLAY artfifacts: the recycle path in `on_order_filled` early-returns without calling `super()`, so the counters (and the fees column) never counted grid fills. |
| the machine idles small (grid progressively smaller) | **False**: grid budget stays nominal; the parked queue simply is not redeployed — that IS the feature. |
| rebalance budget blind to `_recycle_queue` | Part of the design, not a leak: queue = capital WAITING for the R% retrace; on release it moves to `_pending_redistribute` and becomes visible. Adding sum(queue) to the rebalance budget would re-arm it immediately and cancel the retrace wait. |
| `on_order_rejected` never refunds `reserved` (pre-existing defect) | Real defect, **dormant**: 0 rejections in every run (SIM engine accepts everything). Fixed anyway (refund + counter), v2 untouched. |

## Real fixes applied (user subclass only; v2 byte-for-byte untouched)

1. Recycle grid fills now count `n_fills` / `total_commissions` (was skipped
   by the early return).
2. `on_order_rejected` override: refunds `lv.reserved` into `_unallocated`
   and counts `n_rejections` (metrics now surface it).
3. Docstring corrected: interpretation 2 feeds the OPPOSITE side after R%
   (was stale text from interpretation 1's same-side version).

## Diagnostic (5m, R=0.5, INFO logs)

- 2,018 grid fills, 1,946 recycle releases, 570 rebalances, 0 rejections.
- The queue works as designed: releases fire when the R% move happens
  (0.5% retraces are frequent -> R=0.5 behaves almost like no-recycle).

## A/B interpretation 2 (full window, real fees; fixed counters)

| Run | Return % | Max DD % | Ret/DD | Fills | Fees | n_positions | Win % | PF |
|---|---|---|---|---|---|---|---|---|
| **5m stack** (no recycle) | **+7.07** | −5.57 | 1.27 | 2,269 | 2,315.48 | 304 | 71.4 | 1.253 |
| 5m recycle R=0.5% | +5.84 | −4.82 | 1.21 | 2,096 | 2,123.20 | 313 | 71.6 | 1.210 |
| 5m recycle R=1.5% | **−3.66** | −8.41 | −0.43 | 1,696 | 1,719.22 | 263 | 70.7 | 0.856 |
| **1h stack** (no recycle) | +8.41 | −7.73 | 1.09 | 1,125 | 1,191.11 | 226 | 66.8 | 1.201 |
| 1h recycle R=0.5% | +3.20 | −7.80 | 0.41 | 1,141 | 1,202.71 | 232 | 65.5 | 1.072 |
| **1h recycle R=1.5%** | **+9.46** | **−4.95** | **1.91** | 1,059 | 1,099.32 | 244 | 68.0 | 1.254 |

## IMPORTANT correction found this session: the real 1h stack config uses `--rebalance 96` (default), NOT 192

The handoff "exact commands" said: 5m command + `--trend-enter 1.5
--max-exposure-mult 4.0`. Reproducing t12_1h (+8.4057, −7.729, 1,125 fills,
**329 rebalances**) requires the DEFAULT `--rebalance 96`. With 192 the
rebalances are 199 and results differ (my first rerun +8.78 etc. —
misconfigured A/B, thrown out). 5m uses 192 explicitly and reproduces exactly.
HANDOFF command block fixed below. Rule: after every "exact command" copy,
check `n_rebalances` against the doc'd run; they are the canary (bars/interval
± regime re-entries).

## OOS 60/40 for the only promising config (1h R=1.5% vs stack)

Time-sliced (first 60% train = 2022-08 -> 2024-12; last 40% test = -> 2026-08),
same flags.

| Split | Stack | Recycle R=1.5% |
|---|---|---|
| train | **+7.40** / DD −7.73 / retDD 0.96 | +3.87 / DD **−4.22** / retDD 0.92 |
| test | +1.21 / DD −7.15 / retDD 0.17 | **+5.58** / DD **−5.13** / retDD **1.09** |

- DD improves in BOTH splits (that is robust).
- Return: better on test (+4.4pp), worse on train (−3.5pp).
- Mechanism: the queue parks freed capital until the R% move confirms; in a
  trend the queue grows -> less exposure -> less trend bleed (DD) but less
  captured upside (train window contains the Oct23-Mar24 bull leg).

## Verdict (rule 5b: return %, DD, ret/DD)

- **5m: REJECT** (R=0.5: worse return; R=1.5: much worse on both metrics).
- **1h R=1.5%: KEEP-CONDITIONAL.** Better on ALL THREE metrics in the full
  window and on the test split; DD better on both OOS splits; return worse on
  train. It is a chop-protector: low cost to carry, big insurance on DD,
  but it gives up return during strong trends. Flagged for the user's call
  (same grade as Test 2's enter 1.5 keep-conditional). If kept, keep the
  R=1.5 specific threshold (0.5 hurts) and re-check on new data.

## Lessons for BASE_RATES

1. **Metrics counters and engine behavior are different code paths** — a
   wrong-looking result (2,315 -> 78 fills) is first an accounting bug, then
   a result. Rule 7 with the counter in front.
2. **"Exact commands" drift is real**: the doc'd 1h command was wrong
   (n_rebalances 329 vs 199 betrayed it). Canary: totals must reproduce
   exactly, or the config is not what you think.
3. R-recycle is regime-flavored: prior = DD-insurance, not alpha. Regime
   allocation (side multipliers per state) remains the highest-prior feature
   of Test 3; Q multi-volume (sizing only) and SL/V ladders (fee-killed
   individually) get the remaining cheap A/Bs.

## Repro commands

```bash
# 1h A/B (valid base: rebalance 96!): stack + recycle variants, same flags:
python3 e043-state-grid/ag-01/bin/run_backtest_user.py --strategy user \
  --data ../e022-nautilus-sr-grid/ag-01/data/real_btc_1h.csv \
  --out-dir output/nautilus_a/<run> \
  --atr-mult 2.5 --max-levels 2 --min-order 1000 --trend-fast 50 --trend-slow 100 \
  --trend-enter 1.5 --trend-exit 0.5 --rebalance 96 --max-exposure-mult 4.0 \
  --flatten-mode limit_first --flatten-limit-offset-pct 0.05 --flatten-fallback-bars 3 \
  [--recycle-enabled --recycle-pct 1.5]
# 5m A/B: same with real_btc_5m.csv, --trend-enter 0.8, --rebalance 192 (no exposure flag)
```

## Run directory map

| Dir | Meaning |
|---|---|
| `t3_recycle3_5m_r0.5/r1.5`, `t3_recycle4_1h_r0.5/r1.5` | valid A/B runs (fixed counters) |
| `t3_oos_1h_{stack,recycle}_{train,test}` | OOS 60/40 (recycle = R1.5) |
| `t3_recycle2_*`, `diag_recycle_5m` | superseded (broken display counters) |
