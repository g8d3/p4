#!/usr/bin/env bash
# Lightweight timing wrapper.
# Usage:
#   source timer.sh
#   timer_start "step_name"
#   ... do work ...
#   timer_end
#   timer_log  # print summary

TIMING_LOG="${TIMING_LOG:-$(cd "$(dirname "$0")/.." && pwd)/output/timing/timings.csv}"

timer_start() {
    TIMER_NAME="${1:-unnamed}"
    TIMER_START=$(date +%s%3N)
}

timer_end() {
    local end=$(date +%s%3N)
    local elapsed=$(( end - TIMER_START ))
    local ts=$(date -Iseconds)
    mkdir -p "$(dirname "$TIMING_LOG")"
    if [ ! -f "$TIMING_LOG" ]; then
        echo "timestamp,step,duration_ms" > "$TIMING_LOG"
    fi
    echo "$ts,$TIMER_NAME,$elapsed" >> "$TIMING_LOG"
    echo "[TIMING] $TIMER_NAME: ${elapsed}ms ($(( elapsed / 1000 ))s)"
}
