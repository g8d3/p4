#!/usr/bin/env bash
# monitor-cpu.sh — continuously sample CPU/load over time, log it, and notify.
#
# Why: a one-shot `ps`/`top` read misses CPU spikes that go up and come back
# down. Sampling over time (and alerting when a threshold is sustained) is the
# only way to actually see the problem. This is the pattern the user asked for:
#   * register across time (log with timestamps),
#   * notify when it crosses a threshold (via e000-fundamentals/bin/notify.sh
#     -> phone push).
#
# It records:
#   * SYSTEM load average + aggregate CPU% (all processes), and
#   * per-process CPU% for a set of relevant patterns (chrome, node/vite, ...),
# and appends one CSV line per sample to the log.
#
# Usage:
#   bin/monitor-cpu.sh [interval_sec] [logfile] [alert_threshold_pct] [window_samples]
#
# Defaults: interval=5s, logfile=./monitor-cpu.log, alert=false (logging only),
# unless you pass a threshold. With a threshold, after `window_samples`
# consecutive samples above it, it fires one notify.sh push (cooldown 60s).
set -u

INTERVAL="${1:-5}"
LOGFILE="${2:-./monitor-cpu.log}"
THRESHOLD="${3:-0}"          # 0 = disable phone alert, just log
WINDOW="${4:-4}"             # consecutive samples above threshold to alert
COOLDOWN=60                  # seconds between alerts
PROC_PATTERNS="chrome|vite|esbuild|node.*main.js|pi-web|opencode"

last_alert=0

log() { echo "$@"; }

mkts() { date "+%Y-%m-%dT%H:%M:%S"; }

# --- header once ---
[ -s "$LOGFILE" ] || log "timestamp,load_1m,cpu_all%,cpu_vuos%,procs(pat)" > "$LOGFILE"

echo "monitor-cpu: sampling every ${INTERVAL}s -> ${LOGFILE} (alert threshold ${THRESHOLD}%)"
echo "  Ctrl-C / kill to stop. Log is append-only CSV."

last_signal=0
while true; do
  ts=$(mkts)
  load1=$(cut -d' ' -f1 /proc/loadavg)
  # Aggregate CPU: read the AGGREGATE line (starts with "cpu "; ignore "cpu0"
  # per-core lines) twice for a real average. Sum the first 8 counters via awk
  # (robust against an extra trailing counter).
  cpu_prev=$(awk '/^cpu /{s=$2+$3+$4+$5+$6+$7+$8+$9; print s; exit}' /proc/stat)
  idle_prev=$(awk '/^cpu /{print $5+$6; exit}' /proc/stat)
  sleep "$INTERVAL"
  cpu_now=$(awk '/^cpu /{s=$2+$3+$4+$5+$6+$7+$8+$9; print s; exit}' /proc/stat)
  idle_now=$(awk '/^cpu /{print $5+$6; exit}' /proc/stat)
  dtotal=$(( cpu_now - cpu_prev ))
  didle=$(( idle_now - idle_prev ))
  if [ "$dtotal" -gt 0 ]; then
    usage=$(( 100 * (dtotal - didle) / dtotal ))
  else
    usage=0
  fi

  # Per-process CPU for relevant patterns.
  procs=$(ps -eo pcpu,comm,args --sort=-pcpu | grep -iE "${PROC_PATTERNS}" | grep -v grep)
  proc_count=$(echo "$procs" | grep -c . || true)

  # Sum of the matched processes' pcpu.
  pat_cpu=$(echo "$procs" | awk '{s+=$1} END{print (s+0)}')

  log "${ts},${load1},${usage}%,${pat_cpu}%,${proc_count}" >> "$LOGFILE"

  # Alert logic: threshold reached for WINDOW consecutive samples.
  if [ "$THRESHOLD" -gt 0 ] && [ "$usage" -ge "$THRESHOLD" ]; then
    last_signal=$(( last_signal + 1 ))
    now=$(date +%s)
    if [ "$last_signal" -ge "$WINDOW" ] && [ $(( now - last_alert )) -ge "$COOLDOWN" ]; then
      last_alert=$now
      last_signal=0
      msg="CPU sustained ${usage}% (load ${load1}) for ${WINDOW}x${INTERVAL}s — pat procs CPU ${pat_cpu}%, count ${proc_count}"
      echo "  ⚠ ALERT: ${msg}"
      notify_sh=$(find /home/vuos/code/p4/e000-fundamentals/bin -name notify.sh 2>/dev/null | head -1)
      if [ -n "$notify_sh" ]; then
        ( cd /home/vuos/code/p4/e046-kaplay-game && "$notify_sh" info "CPU ALERT: ${msg}" -s monitor-cpu 2>/dev/null ) || true
      fi
    fi
  else
    last_signal=0
  fi
done
