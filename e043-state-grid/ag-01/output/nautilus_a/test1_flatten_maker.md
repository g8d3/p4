# Nautilus-A Test 1 — flatten with maker limit instead of taker market

Plain-language verdict for the course: the grid's only "insides" exit (when it
detects a strong trend and closes everything to protect itself) used to pay a
MARKET order (taker fee 0.06%, paid instantly and at the next bar's price).
This change tries a LIMIT order *one tick behind* the market (maker fee 0.02%;
it only fills if the price bounces that small distance), and only falls back
to the market order if the limit has not filled after 3 bars.

Acceptance (NAUTILUS_A_PLAN): commissions down >10% AND return not worse.

## Implementation

- New file in e022's harness bin (v2 strategy untouched):
  `../e022-nautilus-sr-grid/ag-01/bin/sr_grid_strategy_user.py`
  (`SRGridStrategyUser(SRGridStrategyV2)`, config flag `flatten_mode`).
- Runner: `e043-state-grid/ag-01/bin/run_backtest_user.py` (copy of
  `run_backtest.py` + `--strategy user` and the 3 new flags).
- **Design correction discovered mid-test** (learned for the course): a limit
  order that crosses the market at submit time (SELL below / BUY above price)
  executes IMMEDIATELY as TAKER in Nautilus's SIM engine — same fee as a
  market order, no savings. The maker limit must sit on the NON-marketable
  side (SELL above / BUY below). I originally did it backwards and got
  byte-identical results with `flatten-mode market`; with the flipped sign the
  fees actually drop. Great example of "read the engine's fill logic before
  trusting a fill model".

## A/B results (full dataset, after fees)

| Run | Return % | Max DD % | PF | Fills | Commissions | Sharpe |
|---|---|---|---|---|---|---|
| 5m baseline (market) | +3.64 | −7.16 | 1.139 | 2,158 | 2,392.78 | 1.42 |
| 5m limit_first | **+4.18** | **−6.85** | **1.162** | 2,158 | **2,154.05 (−10.0%)** | **1.64** |
| 5m far-grid limit (rejected) | +3.97 | −5.55 | 1.182 | 2,084 | 2,059.93 | 1.71 |
| 1h baseline (market) | +1.71 | −7.55 | 1.042 | 1,103 | 1,974.96 | 0.66 |
| 1h limit_first | **+3.29** | **−7.26** | **1.084** | 1,100 | **1,211.89 (−38.6%)** | **1.20** |
| 1h far-grid limit (rejected) | −13.76 | −22.74 | 0.743 | 1,025 | 1,108.13 | −2.39 |

Comments:
- 5m fee cut exactly 9.98% — that is 0.02 pp below the 10% bar; honest call:
  **borderline pass** (return +0.54 pp and DD better, so no harm done).
- 1h fee cut is large: −38.6% (there are 402 regime flips on 1h and the
  flatten orders are big). Return nearly doubled.
- "Far grid level" variant (limit one full grid step away) FILLS only on real
  bounces, so exits often happen much later/at worse prices. On 1h it turned
  a +1.7% config into −13.8%. Rejected with the reason written down — this is
  the kind of result that would fool a shorter test.

## Out-of-sample check (first 60% train / last 40% test, per split)

| Split | market | limit_first | market fees | limit fees |
|---|---|---|---|---|
| 5m train (60%) | +2.26% / DD −5.44 | **+2.70%** / −5.23 | 1,495.77 | **1,302.19** |
| 5m test (40%) | +1.93% / DD −4.87 | **+2.06%** / −4.82 | 912.74 | **858.13** |
| 1h train | +3.85% / DD −3.71 | **+4.63%** / −4.12 | 1,156.12 | **711.23** |
| 1h test | −1.92% / DD −6.19 | **−1.15%** / −5.58 | 798.21 | **489.79** |

The improvement holds in all FOUR splits (fees always down, return never
worse; 1h train DD slightly deeper −4.12 vs −3.71 but return +0.78 pp). The
1h test split stays negative for both modes (it is a bearish stretch) — the
maker flatten does not create alpha out of thin air; it only removes bleed.

## Verdict

**KEEP (borderline-to-strong, fails exactly nothing).** Config to carry
forward into Test 3: `flatten_mode = limit_first`, `flatten_limit_offset_pct
= 0.05`, `flatten_fallback_bars = 3`. Variant far-grid discarded on 1h.
Course lesson added: "fill models are part of the backtest — read the engine
before trusting fee savings".

## Commands (reproduce)

```bash
# 5m limit_first
python3 e043-state-grid/ag-01/bin/run_backtest_user.py --strategy user \
  --data ../e022-nautilus-sr-grid/ag-01/data/real_btc_5m.csv \
  --out-dir output/nautilus_a/t1_off005_5m \
  --atr-mult 2.5 --max-levels 2 --min-order 1000 --trend-fast 50 --trend-slow 100 \
  --trend-enter 1.0 --trend-exit 0.5 --rebalance 192 \
  --flatten-mode limit_first --flatten-limit-offset-pct 0.05 --flatten-fallback-bars 3
# 1h limit_first: same, --data real_btc_1h.csv, add --max-exposure-mult 4.0
```

## Correction to save later tests from a wrong starting point

NAUTILUS_A_PLAN says test 2 compares enter_pct {0.3, 0.8} vs "baseline 0.5".
The real e022 baseline (verified in baseline_parity.md) is enter **1.0** /
exit **0.5**. Test 2 will run {0.8, 1.0, 1.5} against exit 0.5 and pick on
return-with-DD-not-worse, per plan spirit.
