# Improvements: ag-01 GPU Browser Capture

## What happened

The capture worked technically (H264 VAAPI encoding, 608×1080 vertical, 8 MB output) but the content was wrong. vkcube rendered its rotating cube fullscreen, completely covering the epiphany browser. GPU utilization averaged only 18.6%.

## Improvements

### 1. Window tiling for both apps visible

The core issue: vkcube runs fullscreen by default, hiding the browser. Use Sway IPC or config to tile windows:

```bash
# Sway config: split layout
workspace 1
layout splith
# Browser top half, vkcube bottom half (or side by side)
```

Or use `swaymsg` to position windows after launch:
```bash
swaymsg [app_id="vkcube"] move position 0 540
swaymsg [app_id="epiphany"] move position 0 0
```

### 2. Increase GPU load

18.6% is low. To saturate the GPU:
- Run multiple vkcube instances: `vkcube --c 1000000 & vkcube --c 1000000 &`
- Use `vkcube --c 1000000 --present_mode 1` (FIFO) for constant rendering
- Open multiple browser tabs with WebGL stress pages
- Add a WebGL2 compute shader benchmark alongside the fragment shader

### 3. Fix capture timing

The recording was 15.2s instead of 10s. The `sleep 10` + `kill` approach has race conditions. Better:
```bash
wf-recorder -f output.mp4 -c h264_vaapi -b 4M --geometry "0,0 608x1080" -t 10
```
The `-t` flag (if available in wf-recorder) or use `timeout 10 wf-recorder ...`

### 4. Capture only the browser region

Instead of capturing the full 608×1080 output, capture just the browser window:
```bash
wf-recorder -f output.mp4 -c h264_vaapi -b 4M \
  --geometry "$(swaymsg -t get_outputs | jq '.[0].rect')" 
```

### 5. Drop vkcube if browser-only is acceptable

If the goal is "browsing the web with GPU stress," vkcube adds complexity. The WebGL fragment shader in webgl-stress.html already does heavy per-pixel computation. With proper window sizing (fullscreen browser), GPU load should be much higher.

### 6. Monitor improvements

The monitor logged 0% CPU throughout — it was monitoring the wrong PID (empty string). Fix:
```bash
# Pass the browser PID to monitor
bash monitor.sh $BROWSER_PID metrics.csv
```

## sudo requirement

Not a limitation for this experiment. Sway needs root for DRM/TTY access. All Wayland apps inherit the sudo environment via `XDG_RUNTIME_DIR` and `WAYLAND_DISPLAY`. The only friction is that sudo commands must go through a separate tmux window.

## Summary

| Issue | Fix |
|-------|-----|
| Browser hidden by vkcube | Sway tiling or window positioning |
| Low GPU (18.6%) | Multiple vkcube instances or fullscreen browser |
| CPU monitor shows 0% | Pass correct PID to monitor.sh |
| Recording too long (15s) | Use `timeout 10` or wf-recorder `-t` flag |
