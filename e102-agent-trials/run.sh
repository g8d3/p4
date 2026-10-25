#!/bin/bash
cd ~/code/p4/e102-agent-trials; mkdir -p mango mangoz runs; A=~/code/p4/e100-openbot/bin/ask.py
for name in "Mango" "Mango Z"; do for k in $(seq 1 240); do s=$(python3 $A --stat "$name"); echo "$s" | grep -q "\"running\"\|null\]" || break; sleep 10; done; echo "$(date -Is) PREDONE $name $s" >> runs/log.txt; done
for n in $(seq -w ${1:-1} 10 | sed "s/^/0/;s/^0\(..\)/\1/"); do
  for a in "Mango:mango" "Mango Z:mangoz"; do
    name=${a%%:*}; dir=${a##*:}
    { printf 'Trial %d/10: ' $((10#$n)); sed "s#{DIR}#$dir#g" tasks/t$n.txt; } > runs/msg_${dir}_$n.txt
    echo "$(date -Is) SENT $n $name prev=$(python3 $A --stat "$name")" >> runs/log.txt
    python3 $A "$name" @runs/msg_${dir}_$n.txt >> runs/log.txt 2>&1
    sleep 5
  done
  for name in "Mango" "Mango Z"; do
    for k in $(seq 1 240); do s=$(python3 $A --stat "$name"); echo "$s" | grep -q '"running"\|null\]' || break; sleep 10; done
    echo "$(date -Is) DONE $n $name $s" >> runs/log.txt
  done
done
echo ALLDONE >> runs/log.txt
