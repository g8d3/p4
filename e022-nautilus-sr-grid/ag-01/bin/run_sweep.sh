#!/usr/bin/env bash
# Run the S/R grid backtest across market regimes and collect a comparison.
#
# For each regime (range, trend, downtrend, mixed):
#   1. Generate synthetic data   -> ag-01/data/synthetic_5m_<mode>.csv
#   2. Run the backtest          -> ag-01/output/<mode>/
#   3. Collect metrics.json
#
# Then print a combined summary table.

set -euo pipefail

AG_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="$AG_DIR/bin"
OUT_ROOT="$AG_DIR/output"
SUMMARY="$OUT_ROOT/summary.csv"

MODES=(range trend downtrend mixed)
SEED=42

rm -f "$SUMMARY"
echo "mode,total_return_pct,total_pnl_usdt,sharpe,max_drawdown_pct,n_fills,n_positions,total_commissions_usdt,profit_factor,win_rate_pct,final_equity_usdt" > "$SUMMARY"

for mode in "${MODES[@]}"; do
  MODE_START=$(date +%s.%N)
  echo "=== mode: $mode ==="
  python3 "$BIN_DIR/gen_synthetic_data.py" \
    --n-bars 20000 --seed "$SEED" --mode "$mode" \
    --out "$AG_DIR/data/synthetic_5m_$mode.csv" > /dev/null

  timeout 500 python3 "$BIN_DIR/run_backtest.py" \
    --data "$AG_DIR/data/synthetic_5m_$mode.csv" \
    --out-dir "$OUT_ROOT/$mode" > /dev/null 2>&1

  m="$OUT_ROOT/$mode/metrics.json"
  if [ ! -f "$m" ]; then
    echo "FAILED: no metrics for $mode"
    echo "$mode,ERROR" >> "$SUMMARY"
    continue
  fi
  python3 - "$mode" "$m" "$SUMMARY" <<'PYEOF'
import json, sys, csv
mode, m, summary = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(m))
row = [mode]
for k in ["total_return_pct","total_pnl_usdt","sharpe","max_drawdown_pct","n_fills","n_positions","total_commissions_usdt","profit_factor","win_rate_pct","final_equity_usdt"]:
    row.append("" if d.get(k) is None else str(d[k]))
with open(summary, "a") as f:
    f.write(",".join(row) + "\n")
print(mode, "return_pct=", d["total_return_pct"], "pnl=", d["total_pnl_usdt"], "fills=", d["n_fills"])
PYEOF
  MODE_END=$(date +%s.%N)
  echo "  mode took $(echo "$MODE_END - $MODE_START" | bc)s"
done

echo
echo "=== SUMMARY ==="
column -s, -t < "$SUMMARY" 2>/dev/null || cat "$SUMMARY"
