
# Session 5 — Seeking Fix

## Diagnosis
Browser seeking was broken because `h264_vaapi` default GOP is 120 frames (~4s at 30fps). Browsers can only seek to I-frames (keyframes). With only one keyframe every 4 seconds, seeking between them required downloading+decoding from the previous keyframe — causing unresponsive scrub.

## Fix
Added `-g 30 -keyint_min 30` to the ffmpeg recording command, forcing a keyframe every 30 frames (~1 second).

## Result
- moov atom: offset 32 ✔️ (faststart)
- Keyframes: every 1.001s (was 4.004s) ✔️
- 19 keyframes in 25s video (was 6 in 35s) ✔️
- Resolution: 608×1080 ✔️
- Audio: aac ✔️
- Integrity: OK ✔️
