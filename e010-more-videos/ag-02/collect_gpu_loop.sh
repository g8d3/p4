#!/bin/bash
# collect_gpu_loop.sh — Collect GPU metrics in a loop
# Usage: ./collect_gpu_loop.sh <output_csv>

OUTPUT_CSV="${1:?Usage: $0 <output_csv>}"

while true; do
    RAW=$(timeout 2 radeontop -d - 2>/dev/null | tail -1 || true)
    if [ -n "$RAW" ]; then
        TS=$(date +%s.%N)
        GPU_PCT=$(echo "$RAW" | grep -oP 'gpu \K[0-9.]+' || echo "0")
        VRAM_USED=$(echo "$RAW" | grep -oP 'vram [0-9.]+% \K[0-9.]+' || echo "0")
        VRAM_PCT=$(echo "$RAW" | grep -oP 'vram \K[0-9.]+' || echo "0")
        MCLK=$(echo "$RAW" | grep -oP 'mclk \K[0-9.]+' || echo "0")
        SCLK=$(echo "$RAW" | grep -oP 'sclk \K[0-9.]+' || echo "0")
        VRAM_TOTAL=$(python3 -c "p=float('${VRAM_PCT}' or '0');u=float('${VRAM_USED}' or '0');print(round(u/(p/100),1) if p>0 else 0)" 2>/dev/null || echo "0")
        echo "$TS,$GPU_PCT,$VRAM_USED,$VRAM_TOTAL,$MCLK,$SCLK" >> "$OUTPUT_CSV"
    fi
    sleep 1
done
