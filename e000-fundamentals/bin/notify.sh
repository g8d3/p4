#!/usr/bin/env bash
# notify.sh — notify completion/errors to the orchestrator log AND the user's phone.
#
# Usage: notify.sh <done|error|info> <message> [-s <sender>] [--test] [--ask "<question>"]
#
#   <message> is MANDATORY (enforced). An empty/whitespace-only call is REJECTED
#   — it never pushes a blank notification. The only exception is `--ask`, whose
#   question supplies the content. This guard exists because AI agents forget the
#   text; instead of silently pushing "(no message)", notify.sh fails loudly so
#   the caller sees the error and fixes it.
#
#   -s <sender>   override the sender (default: auto-detected from CWD —
#                 e.g. "e025-hyperliquid-candle-tails/ag-15-combined")
#   --test        label the message "(manual test)" so receivers know it is
#                 not from an agent
#   --file <path> append a clickable URL to the message, built from
#                 FILEX_BASE_URL (default http://192.168.0.93:9090/code/p4)
#                 + the repo-relative <path>. E.g. the finished video URL.
#   --url <url>   append an arbitrary URL to the message.
#   --ask "...?"  REQUEST ORCHESTRATOR DIRECTION: writes a structured entry
#                 to the orchestrator inbox (~/.opencode/orchestrator-inbox.md)
#                 AND pushes a high-priority phone alert. The orchestrator
#                 reads the inbox whenever it runs; the phone alert tells the
#                 user to point the orchestrator at it.
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
MSG="${2-}"
SENDER=""
TEST=""
ASK=""
FILEX=""
URL=""
while [ $# -gt 2 ]; do
  case "$3" in
    -s) SENDER="$4"; shift 2;;
    --test) TEST=" (manual test)"; shift;;
    --ask) ASK="$4"; shift 2;;
    --file) FILEX="$4"; shift 2;;
    --url) URL="$4"; shift 2;;
    *) shift;;
  esac
done

SUFFIX=""
if [ -n "$URL" ]; then
  SUFFIX=" — $URL"
elif [ -n "$FILEX" ]; then
  BASE="${FILEX_BASE_URL:-http://192.168.0.93:9090/code/p4}"
  SUFFIX=" — $BASE/${FILEX#./}"
fi

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

# --- message is REQUIRED (enforced semantics) ------------------------------
# The point of this service is a meaningful phone signal. An empty or
# whitespace-only message means the caller (often an AI agent) forgot the
# text. Refuse loudly and exit non-zero so the caller notices, instead of
# silently pushing a useless blank notification. `--ask` carries its own
# content, so a lone `notify.sh --ask "..."` stays valid.
if [ -z "${MSG//[[:space:]]/}" ]; then
  if [ -n "${ASK:-}" ]; then
    MSG="(see ask)"
  else
    echo "notify.sh: ERROR: no message text — refusing to send a blank push." >&2
    echo "  Usage: notify.sh <done|error|info> \"<message>\" [-s <sender>] [--test] [--ask \"<?>\"]" >&2
    LOG="${NOTIFY_LOG:-$HOME/.opencode/notifications.log}"
    mkdir -p "$(dirname "$LOG")"
    echo "[$(date -Is)] error [${SENDER:-<unknown>}] notify.sh REJECTED: empty message (caller must pass text)" >> "$LOG"
    exit 1
  fi
fi

LOGFILE="${NOTIFY_LOG:-$HOME/.opencode/notifications.log}"
mkdir -p "$(dirname "$LOGFILE")"
echo "[$(date -Is)] $LEVEL [$SENDER] $MSG$TEST$SUFFIX" >> "$LOGFILE"

TITLE="p4 · $SENDER · $LEVEL"
case "$LEVEL" in
  done)  TAG="white_check_mark"; PRIO="default";;
  error) TAG="warning";             PRIO="high";;
  info)  TAG="information_source";  PRIO="low";;
esac

# --- orchestrator inbox (--ask): structured entry + phone alert -----------
if [ -n "$ASK" ]; then
  INBOX="${ORCHESTRATOR_INBOX:-$HOME/.opencode/orchestrator-inbox.md}"
  mkdir -p "$(dirname "$INBOX")"
  {
    echo
    echo "## $(date -Is) — from $SENDER [$LEVEL]"
    echo "> $MSG"
    echo "**$SENDER asks:** $ASK"
  } >> "$INBOX"
  TAG="rotating_light"
  PRIO="high"
  TITLE="p4 · $SENDER · ORCHESTRATOR REQUEST"
  MSG="$MSG — asks: $ASK"
fi

# --- phone push (the user's channel) --------------------------------------
if [ -n "${NTFY_TOPIC:-}" ]; then
  SERVER="${NTFY_SERVER:-https://ntfy.sh}"
  timeout 10 curl -s -o /dev/null -w "ntfy:%{http_code}\n" \
    -H "Title: $TITLE" -H "Tags: $TAG" -H "Priority: $PRIO" \
    -d "$MSG$TEST$SUFFIX" "$SERVER/$NTFY_TOPIC" >> "$LOGFILE" 2>&1
elif [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  timeout 10 curl -s -o /dev/null -w "telegram:%{http_code}\n" \
    -d "chat_id=$TELEGRAM_CHAT_ID" -d "text=$TITLE: $MSG$TEST$SUFFIX" \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" >> "$LOGFILE" 2>&1
fi

# --- tmux status line (only if inside tmux) ------------------------------
if [ -n "${TMUX:-}" ]; then
  timeout 3 tmux display-message "$TITLE: $MSG$SUFFIX" 2>/dev/null || true
fi

exit 0
