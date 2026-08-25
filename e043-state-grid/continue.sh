#!/usr/bin/env bash
# e043 — context rollover: open a FRESH agent window that continues from HANDOFF.md.
# Usage:
#   ./continue.sh [window]            # default window "43-c"; optional override
#   ./continue.sh 43-1 "custom extra instruction"
#
# The point: when context is full, this is how we reset — summarize -> handoff
# file -> new window -> fresh agent -> continue. No chat history is carried;
# HANDOFF.md + AGENTS.md are the only context.
set -u
EXP_DIR="/home/vuos/code/p4/e043-state-grid"
WIN="${1:-43-c}"
EXTRA="${2:-}"
cd "$EXP_DIR"

# refuse to double-launch on the same window
if tmux has-session -t "$WIN" 2>/dev/null; then
  echo "window $WIN already exists — use a different name"
  exit 1
fi

tmux new-window -n "$WIN" -d
MODEL="opencode-go/deepseek-v4-flash-vision-exp"   # user-required default
tmux send-keys -t "$WIN" "cd $EXP_DIR && opencode -m $MODEL" Enter
# opencode (interactive) needs a few seconds to load, then send the prompt
sleep 6
PROMPT="Read AGENTS.md, then read HANDOFF.md. Follow its NEXT STEP exactly. \
Follow e000-fundamentals guardrails (timeouts, quiet, kill by PID, commit, notify). \
If you need the user: notify.sh --ask with evidence and stop. ${EXTRA}"
tmux send-keys -t "$WIN" "$PROMPT" Enter
echo "launched agent in window '$WIN' (prompt sent). Watch: tmux attach -t $WIN"