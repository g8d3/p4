#!/usr/bin/env bash
# notify.sh — notify completion/errors to the orchestrator log AND the user's phone.
#
# Usage: notify.sh <done|error|info> <message>
#
# Channels (each independent, best-effort, never blocks):
#   1. LOG    — append timestamped line to ~/.opencode/notifications.log (always)
#   2. TTY    — tmux display-message on the current session (visible on the
#               terminal status line if the user is attached)
#   3. PHONE  — push notification, if a channel is configured:
#        ntfy:     NTFY_TOPIC  (and optionally NTFY_SERVER, default https://ntfy.sh)
#        telegram: TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID  (alternative)
#
# No secrets live in this repo — the tokens/topics come from the environment
# (e.g. ~/.zshrc). notify.sh is a thin wrapper; agents call it with one line.
#
# Examples:
#   notify.sh done "ag-15 finished: 312 OOS trades, +0.55%/trade net"
#   notify.sh error "ag-11 GARCH fit crashed: no arch package"
#   notify.sh info "OI collector: r_2 now has N snapshots"

set -u
LEVEL="${1:-info}"
MSG="${2:-(no message)}"
LOGFILE="${NOTIFY_LOG:-$HOME/.opencode/notifications.log}"
EMOJI_DONE="✅"
EMOJI_ERROR="⚠️"
EMOJI_INFO="ℹ️"

mkdir -p "$(dirname "$LOGFILE")"
echo "[$(date -Is)] $LEVEL $MSG" >> "$LOGFILE"

# Channel 2 — tmux status line (only if inside tmux and message is short)
if [ -n "${TMUX:-}" ]; then
  timeout 3 tmux display-message "$EMOJI_DONE$MSG" 2>/dev/null || \
  timeout 3 tmux display-message "$EMOJI_ERROR$MSG" 2>/dev/null || true
fi

# Channel 3 — phone push
TITLE="p4 agent [$LEVEL]"
case "$LEVEL" in
  done)  TAG="white_check_mark"; PRIO="default";;
  error) TAG="warning";             PRIO="high";;
  info)  TAG="information_source";  PRIO="low";;
esac

if [ -n "${NTFY_TOPIC:-}" ]; then
  SERVER="${NTFY_SERVER:-https://ntfy.sh}"
  timeout 10 curl -s -o /dev/null -w "ntfy:%{http_code}" \
    -H "Title: $TITLE" -H "Tags: $TAG" -H "Priority: $PRIO" \
    -d "$MSG" "$SERVER/$NTFY_TOPIC" >> "$LOGFILE" 2>&1
elif [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  timeout 10 curl -s -o /dev/null -w "telegram:%{http_code}" \
    -d "chat_id=$TELEGRAM_CHAT_ID" -d "text=$TITLE: $MSG" \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" >> "$LOGFILE" 2>&1
fi

exit 0
