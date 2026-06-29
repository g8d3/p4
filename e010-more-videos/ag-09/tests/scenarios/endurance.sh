#!/bin/bash
# endurance.sh: 30-minute mixed terminal + browser test
# Simulates realistic long-duration usage patterns

set -euo pipefail
cd "$(dirname "$0")/../.."
SESSION="tds-endurance-$$"
OUTDIR="tests/output/endurance"
mkdir -p "$OUTDIR"
START_TS=$(date +%s)

cleanup() {
    echo ""
    echo "=== Cleanup ==="
    tmux kill-session -t "$SESSION" 2>/dev/null || true
    echo "Duration: $(($(date +%s) - START_TS)) seconds"
    echo "Output: $OUTDIR"
}

trap cleanup EXIT INT TERM

echo "=== TDS Endurance Test (30 min) ==="
echo "Start: $(date)"
echo "Session: $SESSION"

# Create tmux session
tmux new-session -d -s "$SESSION" -x 80 -y 24
sleep 0.5

# Phase 1: Idle (5 min) - terminal sitting at prompt
echo ""
echo "Phase 1/6: Idle (5 min)"
tmux send-keys -t "$SESSION" "echo '=== PHASE 1: IDLE START ==='" Enter
for i in $(seq 1 60); do
    sleep 5
done

# Phase 2: Light work (5 min) - occasional commands
echo ""
echo "Phase 2/6: Light work (5 min)"
tmux send-keys -t "$SESSION" "echo '=== PHASE 2: LIGHT WORK ==='" Enter
for i in $(seq 1 30); do
    case $((RANDOM % 5)) in
        0) tmux send-keys -t "$SESSION" "date" Enter;;
        1) tmux send-keys -t "$SESSION" "whoami" Enter;;
        2) tmux send-keys -t "$SESSION" "pwd" Enter;;
        3) tmux send-keys -t "$SESSION" "ls -la /tmp | head -5" Enter;;
        4) tmux send-keys -t "$SESSION" "uptime" Enter;;
    esac
    sleep $((RANDOM % 10 + 2))
done

# Phase 3: Burst (3 min) - rapid commands
echo ""
echo "Phase 3/6: Burst (3 min)"
tmux send-keys -t "$SESSION" "echo '=== PHASE 3: BURST ==='" Enter
for i in $(seq 1 100); do
    tmux send-keys -t "$SESSION" "echo \"burst line \$i\"" Enter
    sleep 0.1
done

# Phase 4: TUI app (3 min) - htop or equivalent
echo ""
echo "Phase 4/6: TUI app (3 min)"
tmux send-keys -t "$SESSION" "echo '=== PHASE 4: TUI ==='" Enter
if command -v htop &>/dev/null; then
    tmux send-keys -t "$SESSION" "htop" Enter
    sleep 180
    tmux send-keys -t "$SESSION" "q"
elif command -v top &>/dev/null; then
    tmux send-keys -t "$SESSION" "top -b -n 1" Enter
    sleep 5
fi
sleep 10

# Phase 5: Mixed intensity (10 min)
echo ""
echo "Phase 5/6: Mixed (10 min)"
tmux send-keys -t "$SESSION" "echo '=== PHASE 5: MIXED ==='" Enter
for i in $(seq 1 60); do
    case $((RANDOM % 10)) in
        0|1) tmux send-keys -t "$SESSION" "echo \"cmd \$RANDOM\"" Enter;;
        2|3) tmux send-keys -t "$SESSION" "ls /usr/bin | head -20" Enter;;
        4)   tmux send-keys -t "$SESSION" "cat /proc/cpuinfo | head -10" Enter;;
        5)   tmux send-keys -t "$SESSION" "free -h" Enter;;
        6)   tmux send-keys -t "$SESSION" "df -h | head -5" Enter;;
        7)   tmux send-keys -t "$SESSION" "ps aux | head -10" Enter;;
        8)   tmux send-keys -t "$SESSION" "dmesg | tail -20" Enter;;
        9)   tmux send-keys -t "$SESSION" "journalctl -n 20 --no-pager 2>/dev/null || echo 'no journalctl'" Enter;;
    esac
    sleep $((RANDOM % 15 + 2))
done

# Phase 6: Wind down (4 min) - slow output
echo ""
echo "Phase 6/6: Wind down (4 min)"
tmux send-keys -t "$SESSION" "echo '=== PHASE 6: WIND DOWN ==='" Enter
for i in $(seq 1 48); do
    tmux send-keys -t "$SESSION" "echo \"wind down \$i: \$(date)\"" Enter
    sleep $((RANDOM % 10 + 3))
done

tmux send-keys -t "$SESSION" "echo '=== ENDURANCE TEST COMPLETE ==='" Enter

echo ""
echo "=== Endurance test complete ==="
echo "End: $(date)"
echo "Output dir: $OUTDIR"
# Final capture
tmux capture-pane -t "$SESSION" -p > "$OUTDIR/endurance-final.txt"
echo "Final capture: $(wc -c < "$OUTDIR/endurance-final.txt") bytes"
