# ag-08 — Minimal Godot pipe test

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, self-wake pattern

## Command execution
All commands need `timeout`. Use `kill $PID`, never `pkill`. Work in your own directory, never /tmp.

## Goal

Create a minimal 2-second Godot video using the pipe + ffmpeg VAAPI pipeline. Fast feedback loop to debug the pipeline.

## Task

### 1. Create a minimal Godot project in `minimal_test/`

Write test.gd + project.godot inside `minimal_test/`. The script renders a simple colored animation for 2s at 25fps (50 frames). Uses FileAccess to open a named pipe and write raw RGBA data.

### 2. Write and run `run.sh` (background + self-wake)

```
cat > minimal_test/run.sh << 'SCRIPT'
#!/bin/bash
set -e
export LIBVA_DRIVER_NAME=radeonsi
cd minimal_test
rm -f test_pipe
mkfifo test_pipe

timeout 30 ffmpeg -f rawvideo -pix_fmt rgba -s 608x1080 -framerate 25 \
  -i test_pipe \
  -vf "format=nv12,hwupload" -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -y minimal_output.mp4 &
FFPID=$!

timeout 30 godot4 --rendering-driver vulkan --display-driver headless \
  --path .

wait $FFPID 2>/dev/null
rm -f test_pipe
touch done.txt
echo "RENDER COMPLETE"
SCRIPT

chmod +x minimal_test/run.sh
bash minimal_test/run.sh &
RENDER_PID=$!

(sleep 8; tmux send-keys -t a8 "Check minimal_test. PID=$RENDER_PID. Output files?" Enter) &

# Continue working on other things. The self-wake will check progress.
```

### 3. Verify
```
timeout 5 ffprobe minimal_test/minimal_output.mp4 2>/dev/null && echo "OK" || echo "FAIL"
```

### Output
- `minimal_test/recipe.md` — working pipeline or debug notes
