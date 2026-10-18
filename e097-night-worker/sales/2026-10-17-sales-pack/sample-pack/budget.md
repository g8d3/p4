# Turn budget — our own fleet (500 message samples, 2026-10-18)

The formula and the numbers behind it, so the budget can live in your code instead of
in a spreadsheet.

```
cost_per_turn  = (in_tok x price_in + cache_tok x price_cache + out_tok x price_out) / 1e6
wall_per_turn  = boot + pre_response + stream + tools + unexplained
monthly_cost   = cost_per_turn x turns_per_day x 30
```

| term | value | source |
|---|---|---|
| turns/day | 1,000 | your answers |
| turns/year | 250,000 | your answers x workdays |
| wall per turn (p50) | 6.09 s [measured] | measured from your log |
| boot per turn | 372 ms [measured] | measured outside the harness |
| provider roundtrip (p50) | 2836 ms [measured] | measured from your log |
| tokens per turn | ? in / ? out | your answers |
| token line | $1,410/year | `roi.py`, same function as the offer calculator |
| wasted turns | 0.2% | measured on your log |

**The gate that keeps it:** `regression_gate.py` + `baseline.json` (delivered with
Tier 2+). `python3 regression_gate.py --log tps-turns.jsonl --baseline baseline.json`
exits non-zero when wall p50 passes `baseline x 1.2` or the wasted-turn rate passes 5%.
Wire it into the job that runs the loop, and the budget stops being a one-off.
