#!/usr/bin/env bash
# run_one.sh SEED FLAGS... — runs limbo_sim in a per-slot workdir, logs result
SEED="$1"; shift
SLOT="$1"; shift
FLAGS="$@"
SIM=/home/vuos/code/p4/e054-money-agent/turso/target/release/limbo_sim
RES=/home/vuos/code/p4/e054-money-agent/results
WORK=/home/vuos/code/p4/e054-money-agent/workers/w$SLOT
mkdir -p "$WORK"
cd "$WORK" || exit 9
LOG="$RES/sweep-$SLOT.log"
OUT=$("$SIM" -s "$SEED" -t 90 --disable-bugbase $FLAGS 2>&1)
CODE=$?
echo "==== $(date +%H:%M:%S) seed=$SEED slot=$SLOT flags='$FLAGS' exit=$CODE" >> "$LOG"
if [ $CODE -ne 0 ]; then
  echo "$OUT" | tail -80 >> "$LOG"
  echo "FAILURE seed=$SEED flags='$FLAGS' exit=$CODE slot=$SLOT" >> "$RES/failures.log"
  cp -r "$WORK/simulator-output" "/home/vuos/code/p4/e054-money-agent/bugs/s${SEED}_$(echo $FLAGS | tr -c 'a-z0-9' '_')" 2>/dev/null
fi
echo "$CODE $SEED $FLAGS" >> "$RES/sweep-stats.log"
