# ag-08 Recipe — Minimal Godot Video Pipeline

## Result: WORKING (file-based)

## Pipeline
1. Godot headless renders 50 frames (2s @ 25fps) to `frames.raw`
2. ffmpeg VAAPI encodes `frames.raw` → `minimal_output.mp4`
3. Cleanup `frames.raw`, touch `done.txt`

## Files
- `project.godot` — minimal Godot project, forward_plus renderer
- `test.tscn` — scene with Node + test.gd
- `test.gd` — renders colored animation, writes RGBA frames via FileAccess
- `run.sh` — orchestrates Godot + ffmpeg, runs with `timeout`

## Key Findings

### Godot FileAccess + FIFOs: BROKEN
- `FileAccess.open("pipe_path", WRITE)` returns err=12 (`ERR_FILE_CANT_OPEN`)
- Godot's FileAccess does not support named pipes (FIFOs)
- Confirmed with both `ProjectSettings.globalize_path()` and absolute paths
- **Workaround**: write raw frames to file, then encode with ffmpeg after Godot exits

### Working Command
```bash
export LIBVA_DRIVER_NAME=radeonsi
cd minimal_test
timeout 30 godot4 --rendering-driver vulkan --display-driver headless --path .
timeout 30 ffmpeg -f rawvideo -pix_fmt rgba -s 608x1080 -framerate 25 \
  -i frames.raw -vf "format=nv12,hwupload" -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -y minimal_output.mp4
```

## Next Steps
- For streaming (pipe), need alternative: C wrapper, or pipe from Godot stdout, or use Godot's render-to-texture + screenshot approach
- For batch rendering: file-based approach is sufficient
