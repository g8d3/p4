#!/usr/bin/env bash
# run_one2.sh SLOT SEED FLAGS... — robust single job runner
SLOT="$1"; SEED="$2"; shift 2
FLAGS="$@"
SIM=/home/vuos/code/p4/e054-money-agent/turso/target/release/limbo_sim
RES=/home/vuos/code/p4/e054-money-agent/results
WORK=/home/vuos/code/p4/e054-money-agent/workers/x$SLOT
mkdir -p "$WORK"
cd "$WORK" || exit 9
LOG="$RES/sweep-x$SLOT.log"
OUT=$(timeout 500 "$SIM" -s "$SEED" -t 240 -n 3000 --disable-bugbase $FLAGS 2>&1)
CODE=$?
echo "==== seed=$SEED slot=$SLOT flags='$FLAGS' exit=$CODE" >> "$LOG"
if [ $CODE -ne 0 ]; then
  echo "$OUT" | grep -aE "ERROR|panic|integrity|Failed|simulation failed" | tail -30 >> "$LOG"
  echo "FAILURE seed=$SEED flags='$FLAGS' exit=$CODE slot=x$SLOT" >> "$RES/failures.log"
  cp -r "$WORK/simulator-output" "/home/vuos/code/p4/e054-money-agent/bugs/s${SEED}_x" 2>/dev/null
fi
echo "$CODE $SEED $FLAGS" >> "$RES/sweep-stats.log"
