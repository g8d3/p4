#!/bin/bash
# gpu_monitor.sh - Simple GPU monitor for xterm display
while true; do
    clear
    echo "=========================================="
    echo "        GPU RESOURCE MONITOR"
    echo "=========================================="
    echo ""
    timeout 1 radeontop -d - 2>/dev/null | tail -1 | tr ',' '\n' | grep -E "gpu|vram|mclk|sclk" | sed 's/^ //'
    echo ""
    echo "=========================================="
    echo "        $(date '+%H:%M:%S')"
    echo "=========================================="
    sleep 2
done
