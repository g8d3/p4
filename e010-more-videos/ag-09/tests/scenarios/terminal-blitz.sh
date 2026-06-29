#!/bin/bash
# terminal-blitz.sh: pushes terminal capture to the limit
# Tests: rapid output, ANSI codes, full-screen TUIs, parallel output

set -euo pipefail
cd "$(dirname "$0")/../.."  # ag-09 root
SESSION="tds-blitz-$$"
OUTDIR="tests/output/blitz"
mkdir -p "$OUTDIR"

echo "=== TDS Terminal Blitz Test ==="
echo "Session: $SESSION"

# 1. Create a dedicated tmux session for testing
tmux new-session -d -s "$SESSION" -x 80 -y 24
sleep 0.5

# 2. Rapid line output - 5000 lines as fast as possible
echo "--- Test: 5000 lines rapid output ---"
tmux send-keys -t "$SESSION" "for i in \$(seq 1 5000); do echo \"Line \$i: the quick brown fox jumps over the lazy dog \$(date +%s.%N)\"; done" Enter
sleep 3  # let it finish

# 3. TUI full-screen app - htop or btop
echo "--- Test: TUI app (htop) ---"
tmux send-keys -t "$SESSION" "htop" Enter
sleep 2
# Capture during TUI
tmux capture-pane -t "$SESSION" -p > "$OUTDIR/htop-capture.txt"
# Check it captured something meaningful
LINES=$(wc -l < "$OUTDIR/htop-capture.txt")
echo "htop captured: $LINES lines"
if [ "$LINES" -lt 5 ]; then
    echo "WARNING: htop capture too short ($LINES lines)"
fi
# Exit htop
tmux send-keys -t "$SESSION" "q"

# 4. ANSI color explosion
echo "--- Test: ANSI color codes ---"
tmux send-keys -t "$SESSION" "for c in \$(seq 0 255); do printf '\e[48;5;\${c}m \e[0m'; [ \$((c % 16)) -eq 15 ] && echo; done; echo" Enter
sleep 2
tmux capture-pane -t "$SESSION" -p > "$OUTDIR/ansi-capture.txt"
echo "ANSI capture: $(wc -l < "$OUTDIR/ansi-capture.txt") lines"

# 5. Extreme long line (10000 chars)
echo "--- Test: extreme long line ---"
tmux send-keys -t "$SESSION" "printf 'x%.0s' {1..10000}; echo" Enter
sleep 1
tmux capture-pane -t "$SESSION" -p > "$OUTDIR/longline-capture.txt"
echo "Long line capture: $(wc -c < "$OUTDIR/longline-capture.txt") bytes"

# 6. Rapid cursor movement (progress bar / spinner)
echo "--- Test: rapid cursor movement ---"
tmux send-keys -t "$SESSION" $'for i in $(seq 1 100); do printf "\\rProgress: %3d%% [%-50s]" "$i" "$(printf "#%.0s" $(seq 1 $((i/2))))"; sleep 0.05; done; echo' Enter
sleep 6

# 7. Binary data (partial)
echo "--- Test: binary data ---"
tmux send-keys -t "$SESSION" "head -c 5000 /dev/urandom | xxd | head -20" Enter
sleep 1

# 8. Terminal resize during capture
echo "--- Test: resize during capture ---"
tmux send-keys -t "$SESSION" "for i in {1..5}; do echo 'Resize test line $i'; sleep 0.3; done" Enter
# Resize while output is happening
tmux resize-pane -t "$SESSION" -x 120 -y 40
sleep 0.5
tmux resize-pane -t "$SESSION" -x 40 -y 10
sleep 0.5
tmux resize-pane -t "$SESSION" -x 80 -y 24
sleep 1

# 9. Parallel output simulation (two rapid commands)
echo "--- Test: rapid commands ---"
for i in {1..20}; do
    tmux send-keys -t "$SESSION" "echo \"Rapid cmd $i: \$RANDOM\"" Enter
    sleep 0.05
done
sleep 1

# Capture final state
tmux capture-pane -t "$SESSION" -p > "$OUTDIR/final-capture.txt"
echo "Final capture: $(wc -l < "$OUTDIR/final-capture.txt") lines, $(wc -c < "$OUTDIR/final-capture.txt") bytes"

# Cleanup
tmux kill-session -t "$SESSION"
echo ""
echo "=== Blitz test complete ==="
echo "Output files in: $OUTDIR"
wc -c "$OUTDIR"/*.txt 2>/dev/null | tail -1
