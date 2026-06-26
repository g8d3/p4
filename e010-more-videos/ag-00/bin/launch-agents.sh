#!/bin/bash
# launch-agents.sh — Recreate all experiment agent tmux windows
# Run this after a reboot to restore the full multi-agent setup
set -uo pipefail

P4_DIR="/home/vuos/code/p4/e010-more-videos"

# Ensure sway headless is running first
echo "=== Checking sway headless ==="
"$P4_DIR/ag-00/bin/pdw" init 2>/dev/null || echo "sway already running"

# Kill stale agent sessions (in case of partial recovery)
for w in $(tmux list-windows -F '#{window_name}' 2>/dev/null | grep -E '^10-'); do
    tmux kill-window -t "$w" 2>/dev/null
done

launch_agent() {
    local win="$1"
    local dir="$2"
    local prompt="${3:-Read AGENTS.md, then read each file listed in Inherits. Execute the task.}"
    echo "=== Launching $win in $dir ==="
    tmux new-window -n "$win" -d
    tmux send-keys -t "$win" ". ~/.zshrc; cd '$dir' && exec opencode" Enter
    sleep 4
    tmux send-keys -t "$win" "$prompt" Enter
    echo "  $win started"
}

launch_agent "10-1" "$P4_DIR/ag-01"
launch_agent "10-2" "$P4_DIR/ag-02"
launch_agent "10-3" "$P4_DIR/ag-03"
launch_agent "10-5" "$P4_DIR/ag-05"
launch_agent "10-6" "$P4_DIR/ag-06"
launch_agent "10-7" "$P4_DIR/ag-07"

echo "=== All agents launched ==="
echo "Check status: tmux list-windows"
