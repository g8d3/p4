#!/usr/bin/env bash
# Chain status: alive/dead, heartbeat age, epoch count.
cd "$(dirname "$0")/.."
PID=""; [ -f log/chain.pid ] && kill -0 "$(cat log/chain.pid)" 2>/dev/null && PID=$(cat log/chain.pid)
EPOCHS=$(wc -l < history.jsonl 2>/dev/null | tr -d ' ' || echo 0)
HB="never"
if [ -f log/heartbeat ]; then
  HB_AGE=$(( $(date +%s) - $(date -d "$(cat log/heartbeat)" +%s 2>/dev/null || echo 0) ))
  HB="${HB_AGE}s ago"
fi
if [ -n "${PID:-}" ]; then echo "chain: ALIVE pid=$PID heartbeat=$HB epochs=$EPOCHS"; else echo "chain: DEAD heartbeat=$HB epochs=$EPOCHS"; fi
tail -2 LEADERBOARD.md 2>/dev/null | head -1
