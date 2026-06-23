#!/bin/bash
# monitor_gpu.sh - Capture GPU metrics in background
# Usage: ./monitor_gpu.sh <output_csv> <interval_sec>

OUTPUT_CSV="${1:?Usage: $0 <output_csv> <interval_sec>}"
INTERVAL="${2:-1}"

# Write header if file doesn't exist
if [ ! -f "$OUTPUT_CSV" ]; then
    echo "timestamp,gpu_percent,vram_used_mb,vram_total_mb,mclk_ghz,sclk_ghz" > "$OUTPUT_CSV"
fi

while true; do
    # Capture radeontop output for 0.5 seconds
    RAW=$(timeout 1 radeontop -d - 2>/dev/null | tail -1 || true)

    if [ -n "$RAW" ]; then
        TS=$(date +%s.%N)

        # Parse values using grep
        GPU_PCT=$(echo "$RAW" | grep -oP 'gpu \K[0-9.]+' || echo "0")
        VRAM_USED=$(echo "$RAW" | grep -oP 'vram [0-9.]+% \K[0-9.]+' || echo "0")
        VRAM_PCT=$(echo "$RAW" | grep -oP 'vram \K[0-9.]+' || echo "0")
        MCLK=$(echo "$RAW" | grep -oP 'mclk \K[0-9.]+' || echo "0")
        SCLK=$(echo "$RAW" | grep -oP 'sclk \K[0-9.]+' || echo "0")

        # Convert VRAM to MB (estimate total from percentage)
        VRAM_TOTAL=$(python3 -c "
vram_pct = float('${VRAM_PCT}' or '0')
vram_used = float('${VRAM_USED}' or '0')
print(round(vram_used / (vram_pct / 100.0), 1) if vram_pct > 0 else 0)
" 2>/dev/null || echo "0")

        echo "$TS,$GPU_PCT,$VRAM_USED,$VRAM_TOTAL,$MCLK,$SCLK" >> "$OUTPUT_CSV"
    fi

    sleep "$INTERVAL"
done
