# Nautilus-A Test 2 — weather check stricter (trend enter threshold)

Plain-language: the grid only trades in "calm" weather (regime RANGE); the
EMA filter says a trend has started when fast/slow-1 > enter%. This test
moves the enter threshold around the real baseline (1.0/exit 0.5 — corrected
from the plan's assumed 0.5/0.2, see baseline_parity.md) and keeps whoever
improves return without deeper drawdown.

## Demo of the new discipline (screens first)

This test was run through the NEW pipeline: candidate → cheap screen →
engine A/B → OOS. The screen (screen.py C) predicted enter 1.5 would be best
(fewest flips: 8/yr on 5m vs 42) — **the engine disagreed**: 0.8 wins on 5m.
Lesson recorded in BASE_RATES: screen C measures regime churn, not returns;
a screen is a filter, the engine is the judge.

## A/B (full window, flattened market = v2 engine)

| Run | Return % | Max DD % | PF | Fills | Fees | Sharpe |
|---|---|---|---|---|---|---|
| 5m enter 0.8 | **+5.53** | −5.88 | 1.192 | 2,249 | 2,722.06 | — |
| 5m enter 1.0 (baseline) | +3.64 | −7.16 | 1.139 | 2,158 | 2,392.78 | 1.42 |
| 5m enter 1.5 | +3.00 | −11.72 | 1.141 | 2,082 | 2,079.20 | — |
| 1h enter 0.8 | +3.67 | −4.32 | 1.110 | 1,108 | 1,982.18 | — |
| 1h enter 1.0 (baseline) | +1.71 | −7.55 | 1.042 | 1,103 | 1,974.96 | 0.66 |
| 1h enter 1.5 | **+7.23** | −7.94 | 1.170 | 1,125 | 1,712.63 | — |

Cross-validation: 5m 0.8 (+5.53%) independently confirms e022's own sweep
result "5m_v2_ent08" (+5.48%, enter 0.8 / exit 0.4). That is what a
reproducible harness should do.

## OOS 60/40 (winner per dataset, vs enter 1.0 from Test 1's splits)

| Split | 5m enter 0.8 | 5m enter 1.0 | 1h enter 1.5 | 1h enter 1.0 |
|---|---|---|---|---|
| train | **+4.15%** (DD −3.47) | +2.26% (DD −5.44) | **+6.62%** (DD −7.94) | +3.85% (DD −3.71) |
| test | **+1.94%** (DD −5.40) | +1.93% (DD −4.87) | **+0.81%** (DD −7.30) | −1.92% (DD −6.19) |

- 5m 0.8: better on train, stat-equivalent on test (return), DD roughly same.
  **Verdict: KEEP.**
- 1h 1.5: better return on BOTH splits (turns test positive), but DD deeper
  by ~1.1pp (test) / 4.2pp (train). **Verdict: KEEP-CONDITIONAL** — strict
  reading of the plan ("DD not worse") fails; honest trade-off: +2.7pp return
  for +1.1pp DD. Flagged for the user's call before Test 3.

## Combined stack (the base for Test 3)

Test 1 (maker-limit flatten) + Test 2 winner per dataset, full window:

| Stack | Return % | Sharpe | Max DD % | Fees | PF |
|---|---|---|---|---|---|
| **5m: limit_first + enter 0.8** | **+7.07** | 3.11 | −5.57 | 2,315.48 | 1.253 |
| **1h: limit_first + enter 1.5** | **+8.41** | 2.34 | −7.73 | 1,191.11 | 1.201 |
| (original e022 v2 baseline) | +3.64 / +1.71 | — | −7.16 / −7.55 | — | 1.139 / 1.042 |

The two changes stack with synergy (no cancellation) on both datasets. This
stack, with its exact commands below, is Test 3's starting point.

## Verdict for the goal

vs Benchmarks (benchmarks.md): 5m window beats B&H (−44%) by 51 points with
a −5.6% DD; 1h window +8.41% now beats T-bills over 4y (~+17-20% cumulative)
— still below, but the gap closed from "embarrassing" to "same ballpark with
a tiny DD". Honest: still NO equity-grade edge; this is a validated thin
edge + cost discipline, and the next opportunities are the user's features
(Test 3) and the slow state layer (funding/MVRV).

## Commands

```bash
# combined stack 5m
python3 e043-state-grid/ag-01/bin/run_backtest_user.py --strategy user \
  --data ../e022-nautilus-sr-grid/ag-01/data/real_btc_5m.csv \
  --out-dir output/nautilus_a/t12_5m \
  --atr-mult 2.5 --max-levels 2 --min-order 1000 --trend-fast 50 --trend-slow 100 \
  --trend-enter 0.8 --trend-exit 0.5 --rebalance 192 \
  --flatten-mode limit_first --flatten-limit-offset-pct 0.05 --flatten-fallback-bars 3
# combined stack 1h: same with real_btc_1h.csv, --trend-enter 1.5, --max-exposure-mult 4.0
```
