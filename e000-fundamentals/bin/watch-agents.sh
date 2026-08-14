#!/usr/bin/env bash
# watch-agents.sh — persistent watcher for agent completions.
#
# Tails ~/.opencode/notifications.log, and on every new event:
#   1. rewrites ~/.opencode/agent-status.md — a one-glance status snapshot
#      (last event + unanswered orchestrator-inbox requests)
#   2. flashes the tmux status line of the main session (non-intrusive:
#      display-message only, NEVER send-keys — no interference)
#
# The status file is the orchestrator's guaranteed state: any orchestrator
# session reads it as its FIRST action on every turn. The watcher keeps it
# current without anyone remembering to.
#
# Run:  nohup e000-fundamentals/bin/watch-agents.sh >/dev/null 2>&1 &
# Stop: kill $(cat ~/.opencode/watch-agents.pid)
# Restart (after reboot or if it died): re-run the line above.

LOG="${NOTIFY_LOG:-$HOME/.opencode/notifications.log}"
INBOX="${ORCHESTRATOR_INBOX:-$HOME/.opencode/orchestrator-inbox.md}"
STATUS="${AGENT_STATUS:-$HOME/.opencode/agent-status.md}"
PIDFILE="$HOME/.opencode/watch-agents.pid"
POLL=10

echo $$ > "$PIDFILE"
LAST=0
[ -f "$LOG" ] && LAST=$(wc -l < "$LOG")

rewrite_status() {
  local last_line=""
  # strip any glued "ntfy:<code>" tokens from preceding push attempts
  last_line=$(grep -v "^ntfy:" "$LOG" 2>/dev/null | tail -1 | sed -E 's/^ntfy:[0-9]+//')
  local pending=0
  if [ -f "$INBOX" ]; then
    # unanswered = ask entries minus orchestrator replies
    local asks replies
    asks=$(grep -c '\*\*.*asks:\*\*' "$INBOX" 2>/dev/null || echo 0)
    replies=$(grep -c 'Reply (orchestrator' "$INBOX" 2>/dev/null || echo 0)
    pending=$(( asks - replies ))
    [ "$pending" -lt 0 ] && pending=0
  fi
  {
    echo "# Agent status — updated $(date -Is)"
    echo
    echo "- **Last event**: ${last_line:-none}"
    echo "- **Unanswered orchestrator requests**: ${pending:-0} (see \$HOME/.opencode/orchestrator-inbox.md)"
    echo "- **Log**: ${LOG}"
  } > "$STATUS"
}

rewrite_status

while true; do
  sleep "$POLL"
  [ -f "$LOG" ] || continue
  NOW=$(wc -l < "$LOG")
  if [ "$NOW" -gt "$LAST" ]; then
    new_lines=$(tail -n +"$((LAST + 1))" "$LOG" | grep -v "^ntfy:" )
    LAST=$NOW
    if [ -n "$new_lines" ]; then
      # status-line flash on the main session (no send-keys, read-only alert)
      if [ -n "${TMUX:-}" ]; then
        timeout 3 tmux display-message "p4: $(echo "$new_lines" | tail -1 | sed -E 's/^\[[^]]+\] //')" 2>/dev/null || true
      fi
      rewrite_status
    fi
  fi
done
