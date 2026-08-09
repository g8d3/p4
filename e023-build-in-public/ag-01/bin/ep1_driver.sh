#!/bin/bash
# Episode 1 live-run driver — runs the REAL e022 experiment commands
# at human pacing on the sway display. Captured by wf-recorder.
set -u
export TERM=xterm-256color
EXP=/home/vuos/code/p4/e022-nautilus-sr-grid
AG=$EXP/ag-01
OUT=/tmp/opencode/episode1_run
mkdir -p "$OUT"

# helper: run a command in background and show a live elapsed timer
run_long() {
    local label="$1"; shift
    echo -e "\n\033[1;33m▶ $label\033[0m"
    echo -e "\033[2;37m$*\033[0m"
    "$@" > "$OUT/long_run.log" 2>&1 &
    local pid=$!
    local start=$(date +%s)
    while kill -0 "$pid" 2>/dev/null; do
        local el=$(( $(date +%s) - start ))
        printf "\r\033[K   \033[2;37mrunning... %02d:%02d elapsed\033[0m" $((el/60)) $((el%60))
        sleep 3
    done
    wait "$pid"
    local rc=$?
    echo -e "\r\033[K"
    if [ "$rc" -ne 0 ]; then
        echo -e "\033[1;31m   (command exited $rc)\033[0m"
    fi
    sed -E 's/\x1b\[[0-9;]*m//g' "$OUT/long_run.log" | rg -v "matplotlib|Axes3D|warnings.warn|UserWarning" | tail -24
}

pause() {
    echo ""
    sleep "$1"
}

clear
echo -e "\033[1;36m╔══════════════════════════════════════════════════════════════════╗"
echo -e "\033[1;36m║  EPISODE 1 — THE +50% TRADING BOT THAT LOST EVERYTHING        ║"
echo -e "\033[1;36m║  e022 · Nautilus S/R grid strategy · real data reality check  ║"
echo -e "\033[1;36m╚══════════════════════════════════════════════════════════════════╝\033[0m"
pause 4

echo -e "\033[1;32m── 1 · The experiment ──\033[0m"
echo "\$ cd $EXP && ls"
cd "$EXP" || exit 1
ls
pause 3
echo -e "\n\033[2;37mStrategy files:\033[0m"
ls "$AG"/bin/*.py
pause 3
echo -e "\n\033[2;37mWhat the strategy claims to do:\033[0m"
head -30 "$AG/bin/sr_grid_strategy_v2.py" | tail -20
pause 5

echo -e "\n\033[1;32m── 2 · Generate a fake market (synthetic data) ──\033[0m"
echo -e "\033[2;37mCreates 20,000 synthetic 5-min bars that 'look like' a regime-switching market.\033[0m"
run_long "gen_synthetic_data" python3 "$AG/bin/gen_synthetic_data.py" --mode mixed --n-bars 20000
pause 4
echo -e "\n\033[2;37mFirst rows of the fake market:\033[0m"
head -4 "$AG/data/synthetic_5m.csv"
pause 5

echo -e "\n\033[1;32m── 3 · Backtest on a RANGE regime (the 'it works' moment) ──\033[0m"
echo -e "\033[2;37mv1 grid on clean mean-reverting range data. Budget 30k, start 100k.\033[0m"
run_long "backtest range" python3 "$AG/bin/run_backtest.py" --data "$AG/data/synthetic_5m_range.csv" --out-dir "$OUT/range"
pause 5

echo -e "\n\033[1;32m── 4 · The full 4-regime picture ──\033[0m"
echo -e "\033[2;37mSame strategy, all market regimes. Where does it actually work?\033[0m"
cat "$AG/output/summary.csv" | column -t -s,
pause 6

echo -e "\n\033[1;32m── 5 · Parameter search + out-of-sample check (overfit caught) ──\033[0m"
echo -e "\033[2;37m486 configs grid-searched on training data; top configs re-validated on unseen seeds.\033[0m"
python3 "$AG/bin/optimize.py" --status 2>/dev/null | head -8
pause 4
echo -e "\n\033[2;37mTwo top configs, identical except rebalance interval:\033[0m"
python3 - << 'PYEOF'
import csv
rows = list(csv.DictReader(open('/home/vuos/code/p4/e022-nautilus-sr-grid/ag-01/output/optimize/search_results.csv')))
for i in (760, 818):
    r = rows[i]
    print(f"  span {r['grid_span_pct']}  levels {r['max_levels_per_side']}  "
          f"rebalance {r['rebalance_interval_bars']}  cap {r['max_exposure_budget_mult']}x"
          f"  -> TRAIN {r['total_return_pct']}%")
PYEOF
pause 4
echo -e "\n\033[2;37mOut-of-sample verdict (3 unseen seeds) — MIXED regime:\033[0m"
python3 - << 'PYEOF'
import csv
from collections import defaultdict
rows = list(csv.DictReader(open('/home/vuos/code/p4/e022-nautilus-sr-grid/ag-01/output/optimize/validation.csv')))
g = defaultdict(list)
for r in rows:
    if r['mode'] == 'mixed':
        g[r['config']].append(r['total_return_pct'])
for cfg in ('760', '818'):
    seeds = g[cfg]
    mean = sum(float(x) for x in seeds) / len(seeds)
    print(f"  config reb={'48' if cfg=='760' else '96'}: seeds {seeds}  -> mean {mean:+.1f}%")
PYEOF
pause 7

echo -e "\n\033[1;32m── 6 · The reality check: REAL BTC, 5m, one year ──\033[0m"
echo -e "\033[2;37m105,122 real Binance klines. Same 'robust' v1 config from the search. Watch the fees.\033[0m"
run_long "v1 robust on real BTC 5m" python3 "$AG/bin/run_backtest.py" --span 3.5 --max-levels 6 --rebalance 96 --max-exposure-mult 10 --taker-fee 0.0005 --data "$AG/data/real_btc_5m.csv" --out-dir "$OUT/v1_real"
pause 8

echo -e "\n\033[1;32m── 7 · The redesign: v2, same real BTC 5m ──\033[0m"
echo -e "\033[2;37mATR-spaced price-space grid, flat-regime EMA switch, honest leverage, maker fees.\033[0m"
run_long "v2 on real BTC 5m" python3 "$AG/bin/run_backtest.py" --strategy v2 --data "$AG/data/real_btc_5m.csv" --atr-mult 2.5 --max-levels 2 --min-order 1000 --trend-fast 50 --trend-slow 100 --trend-enter 1.0 --trend-exit 0.5 --rebalance 192 --out-dir "$OUT/v2_real"
pause 8

echo -e "\n\033[1;32m── 8 · The full comparison table ──\033[0m"
echo -e "\033[2;37mv1 vs v2 on real BTC, 5m and 1h, after fees.\033[0m"
cat "$AG/output/v2_final_summary.csv" | column -t -s,
pause 8

echo -e "\n\033[1;32m── 9 · Why it works: the interactive explainer ──\033[0m"
echo -e "\033[2;37mReal BTC 1h. Gold band = trend regime, grid flattened. Lines = capital at each level.\033[0m"
google-chrome --ozone-platform=wayland --no-sandbox --no-first-run --disable-gpu-sandbox \
  --window-size=1920,1080 --start-maximized \
  "file://$EXP/interactive/sr-grid-explainer.html" > /dev/null 2>&1 &
CHROME_PID=$!
sleep 18
# try to toggle off help panel for a cleaner visual
echo -e "\033[2;37m(explainer animation running — grid fills, EMA regime flips visible)\033[0m"
sleep 14
kill "$CHROME_PID" 2>/dev/null
sleep 2

echo -e "\n\033[1;32m── VERDICT ──\033[0m"
echo -e "\033[1;36m  Synthetic backtest said:  +50% edge.\033[0m"
echo -e "\033[1;36m  Real BTC 5m, 1 year:      v1 -20.6%  (13,424 fills, 25,235 USDT fees)\033[0m"
echo -e "\033[1;36m  Real BTC 5m, 1 year:      v2  +3.6%  (2,158 fills, 2,393 USDT fees)\033[0m"
echo -e "\033[1;36m  Profit factor 1.14. A modest fee-controlled edge — not a money printer.\033[0m"
echo -e "\033[1;36m  'Profitable in backtest' on synthetic data tells you nothing about real money.\033[0m"
pause 6

echo ""
echo -e "\033[1;33m── capture complete ──\033[0m"
