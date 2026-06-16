# Self-Review: ag-01 GPU Browser Capture

**Model**: Mimo 2.5 (vision)
**Date**: 2026-06-15

## Video Properties

| Property | Value |
|----------|-------|
| Resolution | 608×1080 (vertical) |
| Codec | H.264 (VAAPI) |
| Duration | 15.2s |
| Frames | 913 |
| File size | 8 MB |

## Findings

### WebGL Content Rendering
**Not visible.** The captured frames show only vkcube's rotating LUNARG cube. The epiphany browser with the WebGL stress page is either behind vkcube or not rendering in the capture region.

### GPU Utilization
- **Average GPU busy**: 18.6%
- GPU ramps from 0% → 21% during the recording
- vkcube is actively rendering (cube rotates between frames)
- GPU load is moderate — vkcube alone doesn't saturate the GPU

### Artifacts / Black Frames
- No black frames detected
- Cube renders cleanly with correct textures
- No encoding artifacts visible

### Framing
- 608×1080 vertical format is correct
- vkcube appears in the center-right of the frame
- Large gray empty space on the left and bottom (Sway background)

## Issues

1. **Browser not visible**: vkcube runs fullscreen and covers the epiphany browser. Need to tile or position windows so both are visible.
2. **Low GPU utilization (18.6%)**: Only vkcube is actively rendering. The WebGL stress page should add significant GPU load but isn't contributing.
3. **Capture longer than 10s**: 15.2s recorded instead of 10s (minor timing issue with kill signal).
