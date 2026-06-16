# AI Explorations — June 16, 2026

## Problem Diagnosis: Browser Seeking Broken

### Issue 1: Multiple overlapping Chrome windows
**Root cause**: Chrome processes accumulated across recording sessions. Each `--new-window` call created a new window on the same Xvfb display. After several sessions, 28+ Chrome processes were running with 4+ overlapping windows.

**Fix**: Kill all Chrome processes (`pkill -9 chrome`) before each session. Launch Chrome ONCE with a direct URL (no `--new-window` after first). Use xdotool `ctrl+t` for new tabs instead.

### Issue 2: Native browser player can't seek
**Root cause**: Default VAAPI encoder GOP size is 120 frames. At 30fps that's one keyframe every 4 seconds. Browser video players can only seek to keyframe boundaries — between them they must download + decode from the previous keyframe, making scrubbing unresponsive.

**Evidence**: capture.mp4 had I-frames only at 0.0, 4.0, 8.0, 12.0, 16.0, 20.0, 24.0s.

**Fix**: Added `-g 30 -keyint_min 30` to `ffmpeg` recording, forcing a keyframe every 30 frames (~1 second).

### Fix Validation
1. **Keyframe interval**: Verified with `ffprobe` — I-frames at 0, 1, 2, 3... 19s (was 0, 4, 8, 12...)
2. **FFmpeg seek test**: `time ffmpeg -ss 15 -i capture.mp4 -vframes 1` completes in ~125ms (instant)
3. **Browser seek test**: Served video via `python3 -m http.server`, opened in Chrome, clicked seek bar at 3 different positions — each click produced a different frame (unique MD5 hashes). **Confirmed seeking works.**

### How to test
```bash
# Serve the video
cd ag-03 && python3 -m http.server 9999
# Open in Chrome: http://localhost:9999/capture.mp4
# Click seek bar at multiple positions — video should jump instantly
```
