#!/bin/bash
# E03 (Pro control) live-run driver — runs the REAL e025 commands at human
# pacing on sway HEADLESS-2 (1920x1080). Captured by wf-recorder.
set -u
export TERM=xterm-256color
EXP=/home/vuos/code/p4/e025-hyperliquid-candle-tails

BANNER="\033[1;36m"
DIM="\033[2;37m"
HILITE="\033[1;33m"
GREEN="\033[1;32m"
RED="\033[1;31m"
RESET="\033[0m"

pause() { echo ""; sleep "$1"; }

title() {
  echo -e "\n${BANNER}────────────────────────────────────────────────────${RESET}"
  echo -e "${BANNER}  $1${RESET}"
  echo -e "${BANNER}────────────────────────────────────────────────────${RESET}"
}

clear
echo -e "${BANNER}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "${BANNER}║   THE EDGE HUNT · e025 HYPERLIQUID CANDLES     ║${RESET}"
echo -e "${BANNER}║   15 agents · 135,232 candles · one survivor   ║${RESET}"
echo -e "${BANNER}╚══════════════════════════════════════════════════╝${RESET}"
pause 5

title "ACT 1 · THE QUESTION"
echo -e "${DIM}Can you find a real statistical edge in crypto candles?${RESET}"
echo -e "${DIM}Our rules, declared before we started:${RESET}"
echo -e "${DIM}  1. every finding must survive OUT-OF-SAMPLE${RESET}"
echo -e "${DIM}  2. every finding must survive FEES${RESET}"
echo -e "${DIM}  3. no cherry-picking. nulls are honest results.${RESET}"
pause 7

title "ACT 2 · THE ARMY OF AGENTS"
echo -e "\$ cd $EXP && ls"
cd "$EXP" || exit 1
ls
pause 9
echo -e "${DIM}ag-01 data -> ag-02..04 distributions -> ag-05 seasonality${RESET}"
echo -e "${DIM}-> ag-06 backtest -> ag-07 event study -> ag-08 crash backtest${RESET}"
echo -e "${DIM}-> ag-09 funding -> ag-10 cross-section -> ag-11 vol model${RESET}"
echo -e "${DIM}-> ag-12 regime -> ag-13 fees filter -> ag-14 volume -> ag-15 combined${RESET}"
echo -e "${DIM}-> ag-16 live monitor${RESET}"
pause 8

title "ACT 3 · THE DATASET"
echo -e "${DIM}12 top perps x 4 timeframes (5m/1h/1d/1w), max history.${RESET}"
echo -e "\$ wc -l ag-01-data/output/candles_raw.csv"
wc -l ag-01-data/output/candles_raw.csv
pause 6
echo -e "${DIM}Per-coin candle counts:${RESET}"
echo -e "\$ python3 - <<'PY'"
python3 - << 'PY'
import csv
from collections import Counter
rows = list(csv.DictReader(open('ag-01-data/output/candles_raw.csv')))
n = Counter((r['coin'], r['tf']) for r in rows)
print(f"{'coin':6} {'1d':>6} {'1h':>7} {'5m':>7}")
for coin in ['BTC','ETH','HYPE','SOL','XRP','AAVE','DOGE','CRV']:
    print(f"{coin:6} {n.get((coin,'1d'),0):6d} {n.get((coin,'1h'),0):7d} {n.get((coin,'5m'),0):7d}")
print(f"total candles: {len(rows)}")
PY
pause 9

title "ACT 4 · FINDING 1 — FAT TAILS"
echo -e "${DIM}If returns were a normal bell curve, extreme moves would be rare.${RESET}"
echo -e "${DIM}Measure the tails: kurtosis. Normal = 3. What does crypto say?${RESET}"
echo -e "\$ python3 - <<'PY'  # pooled kurtosis per timeframe"
python3 - << 'PY'
import csv
rows = list(csv.DictReader(open('ag-02-dist/output/stats.csv')))
import statistics as st
from collections import defaultdict
k = defaultdict(list)
for r in rows:
    k[r['tf']].append(float(r['kurtosis']))
for tf in ['5m','1h','1d','1w']:
    v = k[tf]
    print(f"  {tf}: kurtosis {sum(v)/len(v):.1f}  (normal = 3)")
PY
pause 10
echo -e "${DIM}The fat-tail chart — 5m returns vs the normal curve:${RESET}"
echo -e "\$ chafa ag-02-dist/output/charts/hist_5m.png"
chafa --size 96x42 --colors 16 ag-02-dist/output/charts/hist_5m.png
pause 11

title "ACT 5 · FINDING 2 — VOLATILITY CLUSTERING"
echo -e "${DIM}After an extreme move, volatility stays elevated ~2x for several candles.${RESET}"
echo -e "${DIM}Robust, replicated in every coin — but it predicts SIZE, not direction.${RESET}"
echo -e "${DIM}So it's a sizing input, not a trade.${RESET}"
pause 8

title "ACT 6 · THE HONEST NULLS"
echo -e "${DIM}Everything the calendar, order book and funding said about DIRECTION:${RESET}"
echo -e "${DIM}  hour-of-day     -> null${RESET}"
echo -e "${DIM}  day-of-month    -> null${RESET}"
echo -e "${DIM}  weekday effect  -> real pattern, lost out-of-sample${RESET}"
echo -e "${DIM}  funding rates   -> persistent, blind${RESET}"
echo -e "${DIM}  VWAP distance   -> null${RESET}"
echo -e "${DIM}  volume change   -> null${RESET}"
echo -e "${DIM}  OBV divergence  -> dies at fees${RESET}"
pause 11

title "ACT 7 · THE EVENT STUDY — WHAT HAPPENS AFTER A CRASH?"
echo -e "${DIM}Line up every 3-sigma down day, average the 5 days after.${RESET}"
echo -e "\$ sed -n '86,116p' ag-07-event-study/output/report.md"
sed -n '86,116p' ag-07-event-study/output/report.md
pause 11

title "ACT 8 · THE FEES FILTER — THE HYPE FILTER"
echo -e "${DIM}Every trade costs ~0.09% round trip (taker).${RESET}"
echo -e "${DIM}If an edge can't beat that cost, it's dead. Let's check the ledger.${RESET}"
echo -e "\$ cat ag-13-fees-filter/output/edge_ledger.csv"
python3 - << 'PY'
import csv
for r in csv.DictReader(open('ag-13-fees-filter/output/edge_ledger.csv')):
    print(f"  {r['Edge']:26} gross {r['Gross_edge_pct']:>8}  net {r['Net_edge_pct']:>9}  -> {r['Verdict'][:40]}")
PY
pause 13

title "ACT 9 · THE ONE SURVIVOR — COMBINED REVERSION (ag-15)"
echo -e "${DIM}Crash OR low-volume-down -> long 5 days. Walk-forward:${RESET}"
echo -e "${DIM}thresholds from the FIRST half only, trades in the SECOND half.${RESET}"
echo -e "\$ ag-15 combined metrics (OOS second half, net taker)"
python3 - << 'PY'
import json
m = json.load(open('ag-15-combined/output/metrics.json'))
tm = m['trade_metrics']
labels = {'A':'A crash only','B':'B low-vol down','C':'C COMBINED','D':'D both','E':'E always long'}
for k in ['A','B','C','D','E']:
    t = tm[k]
    print(f"  {labels[k]:16} n={t['n']:5d}  mean {t['taker_mean']:+6.2f}%/trade  win {t['taker_win']:5.1f}%  total {m['metrics'][k+'::taker']['total_return']:+7.1f}%")
print()
print("  C: 312 OOS trades. +0.55%/trade net of fees. Sharpe 0.44.")
print("  E: long-only baseline, same window: -67%.")
PY
pause 13
echo -e "${DIM}The equity curves — all five rules, net of taker fees:${RESET}"
echo -e "\$ chafa ag-15-combined/output/equity.png"
chafa --size 96x42 --colors 16 ag-15-combined/output/equity.png
pause 13

title "ACT 10 · THE FORWARD TEST — LIVE PAPER MONITOR (ag-16)"
echo -e "${DIM}The strategy now runs DAILY against live Hyperliquid candles.${RESET}"
echo -e "${DIM}Trigger -> 5-day paper long -> P&L net of fees -> phone push.${RESET}"
echo -e "${DIM}Run it live, right now:${RESET}"
echo -e "\$ cd ag-16-live-monitor && python3 bin/paper_trade.py"
cd "$EXP/ag-16-live-monitor" || exit 1
python3 bin/paper_trade.py
pause 11
echo -e "${DIM}Current paper-trade state:${RESET}"
echo -e "\$ cat output/paper_state.json"
cat output/paper_state.json
pause 8
echo -e "${DIM}Paper-trade log (every real forward trade):${RESET}"
echo -e "\$ cat output/paper_trades.csv"
cat output/paper_trades.csv 2>/dev/null || echo "(no closed trades yet — the honest answer: we wait)"
pause 9

cd "$EXP" || exit 1
title "VERDICT"
echo -e "${GREEN}  15 agents · 135,232 candles · 4 timeframes${RESET}"
echo -e "${GREEN}  Fat tails: kurtosis 9-14 — extreme moves are routine${RESET}"
echo -e "${GREEN}  Vol clustering: real — a sizing input, not a trade${RESET}"
echo -e "${GREEN}  Direction: almost everything null or fee-killed${RESET}"
echo -e "${HILITE}  ONE survivor: daily crash / low-volume-down reversion${RESET}"
echo -e "${HILITE}    312 OOS trades · +0.55%/trade net · Sharpe 0.44${RESET}"
echo -e "${HILITE}    long-only baseline: -67%${RESET}"
echo -e "${RED}  Honest limits: one bear regime, correlated coins, -32% DD${RESET}"
echo -e "${DIM}  Now being paper-traded live, daily. Losses will be shown too.${RESET}"
pause 9

echo ""
echo -e "${BANNER}── capture complete ──${RESET}"
sleep 3
