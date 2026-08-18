#!/usr/bin/env bash
# set-caps.sh — apply/relax the agents cgroup CPU/RAM caps.
# Called by the Cadence mind to enforce or relax the quiet-window caps.
# Usage:
#   set-caps.sh <cpu_percent> <mem_bytes>    # e.g. 150 8589934592
#   set-caps.sh status                        # show current cgroup limits + usage
# Caps are applies to the agents-limited cgroup under user-1000.

CG=/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/agents-limited

case "${1:-status}" in
  status)
    echo "cpu.max      : $(cat $CG/cpu.max 2>/dev/null || echo n/a)"
    echo "memory.max   : $(( $(cat $CG/memory.max 2>/dev/null || echo 0) / 1073741824 ))GiB"
    [ -f $CG/cpu.stat ] && { echo "throttled    : $(grep -c . $CG/cpu.stat >/dev/null; grep nr_throttled $CG/cpu.stat)"; }
    echo "members      : $(wc -l < $CG/cgroup.procs 2>/dev/null || echo 0) procs"
    echo "quiet-override : $(cat $(dirname $0)/quiet-override 2>/dev/null || echo none)"
    ;;
  off)   # user manual off → write override, raise caps to full
    echo "off" > $(dirname $0)/quiet-override
    echo "600000 100000" > $CG/cpu.max
    echo "15032385536" > $CG/memory.max
    echo "quiet OVERRIDE=off, caps at 600%/14GiB until re-enabled"
    ;;
  on)    # user manual on → force quiet regardless of clock
    echo "on" > $(dirname $0)/quiet-override
    echo "150000 100000" > $CG/cpu.max
    echo "8589934592" > $CG/memory.max
    echo "quiet OVERRIDE=on, caps at 150%/8GiB until removed"
    ;;
  schedule) # clear override, revert to the clock's time-window logic
    rm -f $(dirname $0)/quiet-override
    echo "quiet-override cleared; schedule applies (21:00-10:00)"
    ;;
  *)
    cpu_pct="${1:-150}"; mem_bytes="${2:-8589934592}"
    [ "$cpu_pct" -ge 1 ] && [ "$cpu_pct" -le 1200 ] || { echo "bad cpu_pct"; exit 1; }
    quota=$(( cpu_pct * 1000 ))
    echo "$quota 100000" > $CG/cpu.max
    echo "$mem_bytes"    > $CG/memory.max
    echo "caps set: cpu ${cpu_pct}% ($quota/100000 us), mem $(( mem_bytes / 1073741824 ))GiB"
    ;;
esac