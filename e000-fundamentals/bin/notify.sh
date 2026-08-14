#!/usr/bin/env bash
# notify.sh — notify completion/errors to the orchestrator log AND the user's phone.
#
# Usage: notify.sh <done|error|info> <message> [-s <sender>] [--test]
#
#   -s <sender>   override the sender (default: auto-detected from CWD —
#                 e.g. "e025-hyperliquid-candle-tails/ag-15-combined")
#   --test        label the message "(manual test)" so receivers know it is
#                 not from an agent
#
# Channels (each independent, best-effort, never blocks):
#   1. LOG    — ~/.opencode/notifications.log — THE ORCHESTRATOR'S CHANNEL.
#              The orchestrator reads this file to know what finished and when.
#   2. PHONE  — push to the USER's phone, if a channel is configured:
#        ntfy:     NTFY_TOPIC  (and optionally NTFY_SERVER, default https://ntfy.sh)
#        telegram: TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID  (alternative)
#   3. TTY    — tmux display-message on the calling session (when attached).
#
# No secrets in this repo — tokens/topics come from the environment.
#
# Examples:
#   notify.sh done "ag-15 finished: 312 OOS trades, +0.55%/trade net"   # from an agent dir
#   notify.sh error "GARCH fit crashed: arch package missing" -s ag-11
#   notify.sh done "this is a demo" --test

set -u
LEVEL="${1:-info}"
MSG="${2:-(no message)}"
SENDER=""
TEST=""
while [ $# -gt 2 ]; do
  case "$3" in
    -s) SENDER="$4"; shift 2;;
    --test) TEST=" (manual test)"; shift;;
    *) shift;;
  esac
done

# --- sender detection: from CWD if inside a p4 experiment/agent dir ------
if [ -z "$SENDER" ]; then
  CWD="$(pwd 2>/dev/null)"
  if [[ "$CWD" =~ /p4/(e[0-9]{3}-[^/]*)/([^/]+)/?$ ]]; then
    SENDER="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
  elif [[ "$CWD" =~ /p4/(e[0-9]{3}-[^/]*)/?$ ]]; then
    SENDER="${BASH_REMATCH[1]}"
  else
    SENDER="$(hostname -s)"
  fi
fi

LOGFILE="${NOTIFY_LOG:-$HOME/.opencode/notifications.log}"
mkdir -p "$(dirname "$LOGFILE")"
echo "[$(date -Is)] $LEVEL [$SENDER] $MSG$TEST" >> "$LOGFILE"

TITLE="p4 · $SENDER · $LEVEL"
case "$LEVEL" in
  done)  TAG="white_check_mark"; PRIO="default";;
  error) TAG="warning";             PRIO="high";;
  info)  TAG="information_source";  PRIO="low";;
esac

# --- phone push (the user's channel) --------------------------------------
if [ -n "${NTFY_TOPIC:-}" ]; then
  SERVER="${NTFY_SERVER:-https://ntfy.sh}"
  timeout 10 curl -s -o /dev/null -w "ntfy:%{http_code}" \
    -H "Title: $TITLE" -H "Tags: $TAG" -H "Priority: $PRIO" \
    -d "$MSG$TEST" "$SERVER/$NTFY_TOPIC" >> "$LOGFILE" 2>&1
elif [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  timeout 10 curl -s -o /dev/null -w "telegram:%{http_code}" \
    -d "chat_id=$TELEGRAM_CHAT_ID" -d "text=$TITLE: $MSG$TEST" \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" >> "$LOGFILE" 2>&1
fi

# --- tmux status line (only if inside tmux) ------------------------------
if [ -n "${TMUX:-}" ]; then
  timeout 3 tmux display-message "$TITLE: $MSG" 2>/dev/null || true
fi

exit 0
