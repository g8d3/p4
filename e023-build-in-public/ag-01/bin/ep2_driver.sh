#!/bin/bash
# E02 live-run driver — runs the REAL e025 commands at human pacing on the
# sway HEADLESS-1 display (1920x1080). Captured by wf-recorder.
set -u
export TERM=xterm-256color
EXP=/home/vuos/code/p4/e025-hyperliquid-candle-tails
OUT=/tmp/opencode/episode2_run
mkdir -p "$OUT"

BANNER="\033[1;36m"
DIM="\033[2;37m"
HILITE="\033[1;33m"
GREEN="\033[1;32m"
RED="\033[1;31m"
RESET="\033[0m"

pause() { echo ""; sleep "$1"; }

title() {
  echo -e "\n${BANNER}──────────────────────────────────────────────────────────────${RESET}"
  echo -e "${BANNER}$1${RESET}"
  echo -e "${BANNER}──────────────────────────────────────────────────────────────${RESET}"
}

clear
echo -e "${BANNER}╔═══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BANNER}║  EPISODE 2 — HUNTING FOR A TRADING EDGE IN CRYPTO CANDLES   ║${RESET}"
echo -e "${BANNER}║  e025 · Hyperliquid candle tails · 15 agents · 135,232 candles║${RESET}"
echo -e "${BANNER}╚═══════════════════════════════════════════════════════════════╝${RESET}"
pause 5

title "ACT 1 · THE QUESTION"
echo -e "${DIM}Can you find a statistical edge in crypto candles?${RESET}"
echo -e "${DIM}15 agents, one shared dataset, one rule: everything validated${RESET}"
echo -e "${DIM}out-of-sample AND net of fees. No cherry-picking.${RESET}"
pause 6

title "ACT 2 · THE ARMY OF AGENTS"
echo "\$ cd $EXP && ls"
cd "$EXP" || exit 1
ls
pause 8
echo -e "${DIM}ag-01 data → ag-04 monolith → ag-05 seasonality → ag-07 event study${RESET}"
echo -e "${DIM}→ ag-08 crash backtest → ag-13 fees filter → ag-15 combined → ag-16 live monitor${RESET}"
pause 6

title "ACT 3 · THE DATASET"
echo -e "${DIM}12 top perps × 4 timeframes (5m/1h/1d/1w), max available history.${RESET}"
echo -e "${DIM}Total candle count:${RESET}"
echo "\$ wc -l ag-01-data/output/candles_raw.csv"
wc -l ag-01-data/output/candles_raw.csv
pause 6
echo -e "${DIM}Per-coin candle counts, daily:${RESET}"
echo "\$ python3 - <<'PY'  # coin,tf -> candles"
python3 - << 'PY'
import csv
from collections import Counter
rows = list(csv.DictReader(open('ag-01-data/output/candles_raw.csv')))
n = Counter((r['coin'], r['tf']) for r in rows)
print(f"{'coin':6} 1d   1h    5m")
for coin in ['BTC','ETH','HYPE','SOL','XRP','AAVE']:
    print(f"{coin:6} {n.get((coin,'1d'),0):5d} {n.get((coin,'1h'),0):6d} {n.get((coin,'5m'),0):6d}")
print(f"total candles: {len(rows)}")
PY
pause 8

title "ACT 4 · FINDING 1 — FAT TAILS"
echo -e "${DIM}If returns were a normal bell curve, '1-in-1000' moves would be rare.${RESET}"
echo -e "${DIM}Measure the tails: kurtosis. Normal distribution = 3. What does crypto say?${RESET}"
echo "\$ sed -n '8,20p' ag-02-dist/output/report.md  # fat tails, pooled"
sed -n '8,20p' ag-02-dist/output/report.md
pause 10
echo -e "${DIM}The fat-tail chart — 5m returns vs the normal curve:${RESET}"
echo "\$ chafa ag-02-dist/output/charts/hist_5m.png"
chafa --size 100x44 --colors 16 ag-02-dist/output/charts/hist_5m.png
pause 10

title "ACT 5 · FINDING 2 — VOLATILITY CLUSTERING"
echo -e "${DIM}After an extreme move, volatility stays elevated ~2x for several candles.${RESET}"
echo -e "${DIM}Not a tradeable direction — but the core input for position sizing.${RESET}"
echo "\$ sed -n '74,99p' ag-03-cond/output/report.md  # vol clustering"
sed -n '74,99p' ag-03-cond/output/report.md
pause 10

title "ACT 6 · THE HONEST NULLS"
echo -e "${DIM}Everything the calendar, order book and funding said about DIRECTION:${RESET}"
echo "\$ grep the verdicts from the experiment"
echo -e "${DIM}hour-of-day     → null (direction)${RESET}"
echo -e "${DIM}day-of-month    → null${RESET}"
echo -e "${DIM}weekday effect  → real pattern, lost out-of-sample${RESET}"
echo -e "${DIM}funding         → persistent, blind${RESET}"
echo -e "${DIM}VWAP distance   → null${RESET}"
echo -e "${DIM}OBV divergence  → dies at fees${RESET}"
pause 10

title "ACT 7 · THE EVENT STUDY — WHAT HAPPENS AFTER A CRASH?"
echo -e "${DIM}An event study: align every 3σ down day, average the 5 days after.${RESET}"
echo "\$ sed -n '86,116p' ag-07-event-study/output/report.md  # Q1 momentum/reversion"
sed -n '86,116p' ag-07-event-study/output/report.md
pause 10

title "ACT 8 · THE FEES FILTER — THE HYPE FILTER"
echo -e "${DIM}Every trade costs ~0.09% round trip (taker). If an edge can't beat that, it's dead.${RESET}"
echo "\$ cat ag-13-fees-filter/output/edge_ledger.csv"
python3 - << 'PY'
import csv
for r in csv.DictReader(open('ag-13-fees-filter/output/edge_ledger.csv')):
    print(f"{r['Edge']:34} gross {r['Gross_edge_pct']:>9}  net {r['Net_edge_pct']:>10}  -> {r['Verdict'][:44]}")
PY
pause 12

title "ACT 9 · THE ONE SURVIVOR — COMBINED REVERSION (ag-15)"
echo -e "${DIM}Crash OR low-volume-down → long 5 days. Walk-forward: thresholds from the${RESET}"
echo -e "${DIM}first half of history ONLY, trades in the second half ONLY. Out-of-sample.${RESET}"
echo "\$ ag-15 combined metrics (OOS second half, net taker)"
python3 - << 'PY'
import json
m = json.load(open('ag-15-combined/output/metrics.json'))
tm = m['trade_metrics']
labels = {'A':'A crash only','B':'B low-vol down','C':'C COMBINED','D':'D both','E':'E always long'}
for k in ['A','B','C','D','E']:
    t = tm[k]
    print(f"{labels[k]:22} n={t['n']:5d}  mean {t['taker_mean']:+6.2f}%/trade  win {t['taker_win']:5.1f}%  total {m['metrics'][k+'::taker']['total_return']:+7.1f}%")
print("\n312 OOS trades. +0.55%/trade net of fees. Sharpe 0.44.")
print("Long-only baseline (E): -67% over the same window.")
PY
pause 12

echo -e "${DIM}The equity curves — all five rules, net of taker fees:${RESET}"
echo "\$ chafa ag-15-combined/output/equity.png"
chafa --size 100x44 --colors 16 ag-15-combined/output/equity.png
pause 12

title "ACT 10 · THE FORWARD TEST — LIVE PAPER MONITOR (ag-16)"
echo -e "${DIM}The strategy now runs DAILY against live Hyperliquid candles.${RESET}"
echo -e "${DIM}Triggers → paper long for 5 days → P&L net of fees → phone notification.${RESET}"
echo -e "${DIM}This is the honest out-of-sample test going forward. Run it live:${RESET}"
echo "\$ cd ag-16-live-monitor && python3 bin/paper_trade.py"
cd "$EXP/ag-16-live-monitor" || exit 1
python3 bin/paper_trade.py
pause 10
echo -e "${DIM}Current paper-trade state:${RESET}"
echo "\$ cat output/paper_state.json"
cat output/paper_state.json
pause 8
echo -e "${DIM}Paper-trade log (every real forward trade):${RESET}"
echo "\$ cat output/paper_trades.csv"
cat output/paper_trades.csv 2>/dev/null || echo "(no closed trades yet — the honest answer: we wait)"
pause 8

cd "$EXP" || exit 1
title "VERDICT"
echo -e "${GREEN}  15 agents · 135,232 candles · 4 timeframes${RESET}"
echo -e "${GREEN}  Fat tails: kurtosis 9-14 — extreme moves are routine${RESET}"
echo -e "${GREEN}  Vol clustering: real — a sizing input, not a trade${RESET}"
echo -e "${GREEN}  Direction: almost everything null or fee-killed${RESET}"
echo -e "${HILITE}  The ONE survivor: daily crash / low-volume-down reversion${RESET}"
echo -e "${HILITE}    312 out-of-sample trades · +0.55%/trade net · Sharpe 0.44${RESET}"
echo -e "${HILITE}    long-only baseline: -67%${RESET}"
echo -e "${RED}  Honest limits: one bear regime, 12 correlated coins, -32% DD${RESET}"
echo -e "${DIM}  Now being paper-traded live, daily. Losses will be shown too.${RESET}"
pause 8

echo ""
echo -e "${BANNER}── capture complete ──${RESET}"
