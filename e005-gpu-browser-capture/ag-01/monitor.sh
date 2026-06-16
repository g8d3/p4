#!/usr/bin/env bash
set -euo pipefail

# Resource monitor: logs GPU busy%, CPU%, disk write KB/s, memory MB every second
# Usage: monitor.sh <pid_to_monitor> <output_csv>

PID="${1:-}"
CSV="${2:-metrics.csv}"
INTERVAL=1

echo "timestamp,gpu_busy_pct,cpu_pct,disk_write_kbps,memory_mb" > "$CSV"

GPU_PATH="/sys/class/drm/card1/device/gpu_busy_percent"

# Get disk stats for the mount point of the output directory
DISK_DEV=$(df --output=source "$(dirname "$CSV")" 2>/dev/null | tail -1)

prev_wr=0
first=1

while true; do
  TS=$(date -Iseconds)

  GPU=$(cat "$GPU_PATH" 2>/dev/null || echo 0)

  CPU=0
  MEM=0
  if [ -n "$PID" ] && [ -d "/proc/$PID" ]; then
    STAT=$(cat "/proc/$PID/stat" 2>/dev/null || true)
    if [ -n "$STAT" ]; then
      CLK_TCK=$(getconf CLK_TCK 2>/dev/null || echo 100)
      # utime(13) + stime(14) = fields 13,14 (0-indexed: 12,13)
      UTIME=$(echo "$STAT" | cut -d' ' -f13)
      STIME=$(echo "$STAT" | cut -d' ' -f14)
      TOTAL=$((UTIME + STIME))
      if [ "$first" -eq 1 ]; then
        first=0
      else
        CPU=$(( (TOTAL - PREV_TOTAL) * 100 / INTERVAL / CLK_TCK ))
      fi
      PREV_TOTAL=$TOTAL
    fi
    MEM=$(awk '/VmRSS/ {printf "%.0f", $2/1024}' "/proc/$PID/status" 2>/dev/null || echo 0)
  fi

  DISK_WR=0
  if [ -n "$DISK_DEV" ]; then
    DISK_DEV_BASE=$(basename "$DISK_DEV" 2>/dev/null || echo nvme0n1)
    DISK_RAW=$(cat "/sys/block/$DISK_DEV_BASE/stat" 2>/dev/null | awk '{print $7 * 512 / 1024}' | cut -d. -f1 || echo 0)
    if [ "$prev_wr" -ne 0 ] 2>/dev/null; then
      DISK_WR=$(( (DISK_RAW - prev_wr) / INTERVAL ))
    fi
    prev_wr=$DISK_RAW
  fi

  echo "$TS,$GPU,$CPU,$DISK_WR,$MEM" >> "$CSV"
  sleep "$INTERVAL"
done
