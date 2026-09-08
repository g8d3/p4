#!/usr/bin/env bash
# driver.sh — consume jobs from jobs/jobs.txt with 11 parallel slots
cd /home/vuos/code/p4/e054-money-agent
JOBS=jobs/jobs.txt
LOCK=jobs/lock
SLOTS=11
next_job() {
  # atomic-ish line pop using flock
  flock "$LOCK" bash -c '
    head -1 '"$JOBS"' 2>/dev/null
    sed -i "1d" '"$JOBS"' 2>/dev/null
  '
}
slot() {
  local SLOT=$1
  while true; do
    JOB=$(next_job)
    [ -z "$JOB" ] && break
    SEED="${JOB%%|*}"
    FLAGS="${JOB#*|}"
    ./run_one.sh "$SEED" "$SLOT" $FLAGS
  done
}
for i in $(seq 0 $((SLOTS-1))); do
  slot $i &
done
wait
echo "ALL DONE" > results/DONE
