# ag-02 — GPU screen capture research

## Goal

Determine whether GPU-based screen capture can record multiple screen regions simultaneously at real-time speed.

## Research questions

1. Is VAAPI or NVENC available for hardware-accelerated encoding?
2. Can ffmpeg capture multiple x11grab regions concurrently with hardware encoding?
3. What is the performance difference vs current CPU approach (608x1080, 15fps)?
4. Can it scale to 4+ simultaneous recordings?

## Method

1. Check available hardware encoders:
   ```
   ffmpeg -encoders 2>/dev/null | grep -iE "h264|hevc|nvenc|vaapi|qsv"
   ffmpeg -hide_banner -hwaccels
   vainfo 2>/dev/null || echo "no VAAPI"
   nvidia-smi 2>/dev/null || echo "no NVIDIA"
   ```

2. Test single GPU capture:
   ```
   ffmpeg -vaapi_device /dev/dri/renderD128 -f x11grab -video_size 608x1080 -i :0.0+656,0 -c:v h264_vaapi output.mp4
   ```

3. Test parallel captures (two regions at once).

4. Measure: CPU usage, GPU usage, FPS, latency.

## Deliverable

Write findings to `notes.md` with:
- Hardware available
- Commands tested
- FPS/resource numbers
- Conclusion: can we scale to N simultaneous recordings?
- Recommendation for next steps
