#!/usr/bin/env bash
# e073 chain dispatcher: completion-triggered, NOT clock-triggered.
# One epoch runs; the moment it finishes, the next starts.
# A 3-minute epoch chains at minute 3; a 5-minute one at minute 5.
# Control: STOP file ends the chain gracefully after the current epoch.
#   touch STOP   -> chain exits after current tick
#   rm STOP      -> start again with: nohup bin/chain.sh >> log/chain.log 2>&1 &
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p log
BREATH="${CHAIN_BREATH_SEC:-3}"  # seconds between ticks (log flush, not a schedule)
FAIL_SLEEP="${CHAIN_FAIL_SLEEP:-60}"

echo $$ > log/chain.pid
echo "$(date -u +%FT%TZ) CHAIN start pid=$$"
while true; do
  if [ -f STOP ]; then
    echo "$(date -u +%FT%TZ) CHAIN stop requested, exiting"
    exit 0
  fi
  # LLM legs first: if the queue holds tasks, an agent works (bounded, locked).
  # Queue empty -> decider queues the next outward task (throttled 20 min).
  # Fee ticks (free) fill the gaps between intelligence.
  if [ -s LEG_QUEUE ]; then
    bash bin/llm-leg.sh >> log/tick.log 2>&1 || true
    date -u +%FT%TZ > log/heartbeat
  elif [ ! -f log/last-decide ] || [ $(( $(date +%s) - $(date -d "$(cat log/last-decide)" +%s 2>/dev/null || echo 0) )) -gt 1200 ]; then
    bash bin/decide.sh >> log/tick.log 2>&1 || true
    date -u +%FT%TZ > log/heartbeat
  fi
  if bash bin/tick.sh >> log/tick.log 2>&1; then
    date -u +%FT%TZ > log/heartbeat
  else
    echo "$(date -u +%FT%TZ) CHAIN tick failed, sleeping ${FAIL_SLEEP}s" >> log/chain.log
    sleep "$FAIL_SLEEP"
    continue
  fi
  sleep "$BREATH"
done
