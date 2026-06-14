# ag-08 — Weston + wf-recorder VAAPI test

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, self-wake pattern

## Command execution
ALL commands in background with &. Self-wake with sleep N. Never run anything synchronously.

## Goal

Test the pure GPU pipeline: Weston headless → wf-recorder with VAAPI → MP4. No CPU encoding, no disk writes.

## Task

### 1. Start Weston headless (background)
```
weston --backend=headless --renderer=gl --socket=wayland-test &
(sleep 3; tmux send-keys -t a8 "Self-wake: check weston socket" Enter) &
```

### 2. Record with wf-recorder (VAAPI GPU)
```
WAYLAND_DISPLAY=wayland-test timeout 10 wf-recorder -f test_output.mp4 \
  -c h264_vaapi -x yuv420p -b 2M &
REC_PID=$!
(sleep 2; tmux send-keys -t a8 "Self-wake: PID=$REC_PID recording. Check: ls -lh test_output.mp4" Enter) &
```

### 3. Open a colored window in Weston for reference (optional)
```
WAYLAND_DISPLAY=wayland-test timeout 5 weston-simple-egl 2>/dev/null &
(sleep 6; tmux send-keys -t a8 "Self-wake: check if wf-recorder captured anything" Enter) &
```

### 4. Verify output
```
ffprobe test_output.mp4 2>&1 | grep -i "Stream\|Duration"
echo "=== GPU used? ==="
cat /sys/class/drm/card*/device/gpu_busy_percent
```

### 5. Log results
Write `wf-test.md` with:
- Working commands
- Resource usage (GPU%, CPU%, disk writes)
- Comparison to previous methods
- Recommendation for ag-04

## Execute

Read this file entirely. Then follow the steps above in order. Each command in background with &. Self-wake after each step. Never run anything synchronously.

## Cleanup
```
rm -f test_output.mp4
timeout 5 kill $WESTON_PID 2>/dev/null
```
