#!/usr/bin/env bash
# One Edge Terminal agent cycle. Safe to run forever: idempotent, read-only on
# money, honours data/LOOP_STOP, appends one row per cycle.
#
#   bash bin/loop.sh          # one cycle
#   bash bin/loop.sh watch    # forever (every 300s) until LOOP_STOP exists
#   touch data/LOOP_STOP      # stop a watch loop
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p data log

if [ -f data/LOOP_STOP ]; then
  echo "LOOP_STOP present — not running. rm data/LOOP_STOP to resume."
  exit 0
fi

run_cycle() {
  python3 bin/loop.py >>log/loop.log 2>&1
  local rc=$?
  [ $rc -ne 0 ] && echo "cycle failed rc=$rc (see log/loop.log)"
  return $rc
}

case "${1:-one}" in
  one) run_cycle ;;
  watch)
    echo "watching every 300s — touch data/LOOP_STOP to stop"
    while [ ! -f data/LOOP_STOP ]; do
      run_cycle
      # sleep in small slices so LOOP_STOP takes effect quickly
      for _ in $(seq 1 60); do [ -f data/LOOP_STOP ] && break; sleep 5; done
    done
    echo "LOOP_STOP seen — exiting"
    ;;
  *) echo "usage: $0 [one|watch]"; exit 1;;
esac
