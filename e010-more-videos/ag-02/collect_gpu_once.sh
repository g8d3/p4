#!/bin/bash
# collect_gpu_once.sh - Collect a single GPU sample
# Usage: ./collect_gpu_once.sh >> output.csv

RAW=$(timeout 2 radeontop -d - 2>/dev/null | tail -1 || true)
if [ -n "$RAW" ]; then
    TS=$(date +%s.%N)
    GPU_PCT=$(echo "$RAW" | grep -oP 'gpu \K[0-9.]+' || echo "0")
    VRAM_USED=$(echo "$RAW" | grep -oP 'vram [0-9.]+% \K[0-9.]+' || echo "0")
    VRAM_PCT=$(echo "$RAW" | grep -oP 'vram \K[0-9.]+' || echo "0")
    MCLK=$(echo "$RAW" | grep -oP 'mclk \K[0-9.]+' || echo "0")
    SCLK=$(echo "$RAW" | grep -oP 'sclk \K[0-9.]+' || echo "0")
    VRAM_TOTAL=$(python3 -c "p=float('${VRAM_PCT}' or '0');u=float('${VRAM_USED}' or '0');print(round(u/(p/100),1) if p>0 else 0)" 2>/dev/null || echo "0")
    echo "$TS,$GPU_PCT,$VRAM_USED,$VRAM_TOTAL,$MCLK,$SCLK"
fi
