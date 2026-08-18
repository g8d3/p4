#!/usr/bin/env bash
# spawn-agent.sh — launch a successor agent from its successor.md.
# THE reproduction mechanism: an agent that finishes leaves a successor.md;
# Cadence (or the orchestrator) calls this to actually START the next agent.
#
# Usage:
#   spawn-agent.sh <agent-id> <window> <agent-dir>
#     — reads <agent-dir>/../output/successor.md for the launch prompt
#       (falls back to AGENTS.md's own Inherits + Execute prompt)
#   spawn-agent.sh <agent-id> <window> <agent-dir> "<prompt>"
#     — explicit prompt, no successor.md needed
#
# Does, in order:
#   1. refusals if the window already exists or the agent is already in config
#   2. tmux new-window named <window>, cd into agent-dir, opencode (deepseek-v4-flash)
#   3. wait for the Build status bar (or the cmd equivalent), then send the prompt
#   4. register the agent in the cadence config.json (booting phase)
#   5. move the process tree into the agents-limited cgroup
#   6. print the agent id + window it launched into

set -u
AGENT="${1:?agent-id required, e.g. ag-07}"
WIN="${2:?window required, e.g. 32-7}"
DIR="${3:?agent dir required}"
PROMPT="${4:-}"

PM=/home/vuos/code/p4/e000-fundamentals/bin/progress-monitor
CFG=$PM/config.json
CG=/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/agents-limited

# refusals
if tmux has-session -t "$WIN" 2>/dev/null || tmux list-windows -t main -F '#{window_name}' 2>/dev/null | grep -qx "$WIN"; then
  echo "REFUSE: window '$WIN' already exists"; exit 1
fi
if python3 -c "import json,sys; c=json.load(open('$CFG')); sys.exit(0 if '$AGENT' in c['agents'] else 1)" 2>/dev/null; then
  echo "REFUSE: agent '$AGENT' already registered"; exit 1
fi

# resolve the prompt: explicit > successor.md > default
if [ -z "$PROMPT" ] && [ -f "$DIR/output/successor.md" ]; then
  # extract the Launch-ready prompt block (between the heading and the next ---)
  PROMPT=$(awk '/^## Launch-ready prompt/{f=1;next} /^```$/{if(f){f=0}} f' "$DIR/output/successor.md" 2>/dev/null \
           | sed '/^```$/d' | tr '\n' ' ' | sed 's/  */ /g')
fi
[ -z "$PROMPT" ] && PROMPT="Read AGENTS.md, then read each file listed in Inherits. Execute the task."

mkdir -p "$DIR/output"
tmux new-window -n "$WIN" -d
tmux send-keys -t "$WIN" "cd $DIR && opencode -m opencode-go/deepseek-v4-flash" Enter

# readiness: wait for the Build status bar (or cmd) up to 20s
for i in $(seq 1 20); do
  pane=$(tmux capture-pane -t "$WIN" -p 2>/dev/null)
  echo "$pane" | grep -qE "Build|DeepSeek|Command|⌘" && break
  sleep 1
done
sleep 1
tmux send-keys -t "$WIN" "$PROMPT" Enter

# register in cadence config
python3 - "$AGENT" "$WIN" "$DIR" << 'PYEOF'
import json, sys
agent, win, d = sys.argv[1], sys.argv[2], sys.argv[3]
p = "/home/vuos/code/p4/e000-fundamentals/bin/progress-monitor/config.json"
cfg = json.load(open(p))
cfg["agents"][agent] = {
  "dir": d + "/output",
  "window": win,
  "task": "successor (auto-spawned)",
  "phase": "booting",
  "base_intervals_s": {"booting": 30, "working": 60, "long-step": 300, "done": 600},
  "idle_mult": 2, "stuck_mult": 4,
  "step_back": {"max_multiplier": 4, "stable_cycles_needed": 3, "grow_by": 1.5}
}
json.dump(cfg, open(p, "w"), indent=2)
PYEOF

# cap into quiet cgroup
PID=$(tmux list-panes -t "$WIN" -F '#{pane_pid}' 2>/dev/null)
for p in $(pgrep -P "$PID" 2>/dev/null) "$PID"; do echo "$p" > "$CG/cgroup.procs" 2>/dev/null; done

echo "spawned $AGENT in window $WIN (dir $DIR)"