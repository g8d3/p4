# Nautilus-A Test 0 — e022 v2 baseline parity

Goal: reproduce the published e022 v2 numbers in e043 on e022's real Nautilus
harness (`../e022-nautilus-sr-grid/ag-01/bin/run_backtest.py --strategy v2`).
Full parity is the gate for the A/B tests in NAUTILUS_A_PLAN.md.

## Result — PASS (exact parity, all metrics)

| Dataset | Config | Metric | Published | Reproduced | Delta |
|---|---|---|---|---|---|
| BTC 5m 1y | atr 2.5, lv 2, reb 192, trend 50/100 | Return % | +3.6449 | +3.6449 | 0 |
|  |  | Max DD % | −7.1628 | −7.1628 | 0 |
|  |  | PF | 1.1386 | 1.1386 | 0 |
|  |  | Fills | 2,158 | 2,158 | 0 |
|  |  | Commissions | 2,392.78 | 2,392.78 | 0 |
| BTC 1h 4y | reb 96, cap 4×, trend 50/100 | Return % | +1.7133 | +1.7133 | 0 |
|  |  | Max DD % | −7.5511 | −7.5511 | 0 |
|  |  | PF | 1.0418 | 1.0418 | 0 |
|  |  | Fills | 1,103 | 1,103 | 0 |
|  |  | Commissions | 1,974.96 | 1,974.96 | 0 |

All other fields also match exactly: 5m sharpe 1.4207, n_regime_flips 86,
n_resyncs 926; 1h sharpe 0.6614, n_regime_flips 402, n_resyncs 561.

## Commands

```bash
# 5m (out: output/nautilus_a/5m_baseline/)
python3 ../e022-nautilus-sr-grid/ag-01/bin/run_backtest.py --strategy v2 \
  --data ../e022-nautilus-sr-grid/ag-01/data/real_btc_5m.csv \
  --out-dir ag-01/output/nautilus_a/5m_baseline \
  --atr-mult 2.5 --max-levels 2 --min-order 1000 \
  --trend-fast 50 --trend-slow 100 --trend-enter 1.0 --trend-exit 0.5 \
  --rebalance 192

# 1h (out: output/nautilus_a/1h_baseline/)
python3 ../e022-nautilus-sr-grid/ag-01/bin/run_backtest.py --strategy v2 \
  --data ../e022-nautilus-sr-grid/ag-01/data/real_btc_1h.csv \
  --out-dir ag-01/output/nautilus_a/1h_baseline \
  --atr-mult 2.5 --max-levels 2 --min-order 1000 \
  --trend-fast 50 --trend-slow 100 --trend-enter 1.0 --trend-exit 0.5 \
  --max-exposure-mult 4.0
```

## Notes

- Exact commands were recovered from e022's own sweep logs
  (`v2_sweep_5m_final.csv`, `v2_sweep_1h_final.csv`) — the metrics match
  e022 `output/v2_5m/metrics.json` and `output/v2_1h/metrics.json` field by
  field, so the harness itself is cloned faithfully.
- Config correction vs HANDOFF.md: both published baselines actually use
  trend EMA 50/100 with enter 1.0 / exit 0.5 (not 20/100/0.5/0.2). The
  1h "cap 4×" knob is `--max-exposure-mult 4.0`; 5m also uses cap 4.0 and
  `--rebalance 192` (default is 96). Values in the NAUTILUS_A_PLAN baseline
  table stay valid: state-grid decision layer must beat +3.64% (5m) and
  +1.71% (1h) after fees in this harness.
- Environment: Nautilus Trader 1.228.0, system python3. Runtime ~10s each.
- Next: A/B tests 1–3 in NAUTILUS_A_PLAN.md, one change at a time, each on
  the exact commands above.
