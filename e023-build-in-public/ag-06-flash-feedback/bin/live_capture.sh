#!/usr/bin/env bash
# Live-run capture for the e025 episode. Drives a real foot+tmux terminal on
# HEADLESS-4, runs real commands, and grim-screenshots each key moment.
# Usage: live_capture.sh   (terminal must already be launched)
set -u
export SWAYSOCK=/run/user/1000/sway-ipc.1000.240699.sock
export WAYLAND_DISPLAY=wayland-1
FR=/home/vuos/code/p4/e023-build-in-public/ag-06-flash-feedback/output/frames
E=/home/vuos/code/p4/e025-hyperliquid-candle-tails

shot() { grim -o HEADLESS-4 "$1"; }

say() { tmux send-keys -t h4term "$1" Enter; sleep "$2"; }

# 1. data fetch — wc -l candles_raw.csv
say "clear" 1
say "cd $E/ag-01-data/output && wc -l candles_raw.csv" 2
shot "$FR/real_data.png"

# 2. kurtosis stats — real numbers per coin (1d)
say "clear" 1
say "cd $E/ag-02-dist/output" 1
say "head -1 stats.csv | cut -d, -f1,2,7" 1
say "grep ',1d,' stats.csv | cut -d, -f1,2,7 | column -t -s," 2
shot "$FR/real_stats.png"

# 3. edge ledger — fees filter verdicts
say "clear" 1
say "cd $E/ag-13-fees-filter/output" 1
say "python3 -c \"import csv; r=list(csv.DictReader(open('edge_ledger.csv'))); [print(f\\\"{x['Edge'][:30]:30s} {x['Net_edge_pct'][:12]:12s} {x['Verdict'][:40]}\\\") for x in r[:5]]\"" 2
shot "$FR/real_ledger.png"

# 4. live paper monitor run
say "clear" 1
say "cd $E/ag-16-live-monitor" 1
say "python3 bin/paper_trade.py --dry-run" 18
shot "$FR/real_monitor.png"

# 5. monitor state — pending AAVE
say "cat output/paper_state.json" 2
shot "$FR/real_monitor_state.png"

# 6. event study — +2.47% mean next-5 for 46 down events
say "clear" 1
say "cd $E/ag-07-event-study/output" 1
say "head -1 splits.csv" 1
say "grep 'down,1d' splits.csv | head -2" 2
shot "$FR/real_eventstudy.png"

# 7. honest nulls — funding verdict
say "clear" 1
say "cd $E/ag-09-funding/output" 1
say "grep -i -A1 'Verdict' report.md | head -6" 2
shot "$FR/real_nulls.png"

echo "=== live capture done ==="
ls -la "$FR"/real_*.png
