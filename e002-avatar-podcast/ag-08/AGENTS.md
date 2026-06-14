# ag-08 — Minimal Godot pipe test

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, self-wake pattern

## Command execution
All commands need `timeout`. Use `kill $PID`, never `pkill`.

## Goal

Create a minimal 2-second Godot video using the pipe + ffmpeg VAAPI pipeline. This is a fast feedback loop to debug the pipeline without rendering the full 4:30 video.

## Task

### 1. Create a minimal Godot project

Write a minimal GDScript that renders a colored animation (e.g., a moving square) for 2 seconds at 25fps, writing raw RGBA frames to a pipe.

```
mkdir -p minimal_test
cat > minimal_test/test.gd << 'EOF'
extends Node

var frame_count = 0
var target_frames = 50  # 2 seconds at 25fps
var pipe: FileAccess
var pos = 0.0

func _ready():
	pipe = FileAccess.open("/tmp/test_pipe", FileAccess.WRITE)
	if pipe == null:
		printerr("FAIL: Cannot open pipe")
		get_tree().quit(1)
		return
	print("Pipe opened OK")

func _process(delta):
	if frame_count >= target_frames:
		pipe.close()
		print("DONE: ", frame_count, " frames")
		get_tree().quit()
		return
	
	# Draw a simple frame
	pos += 0.05
	var img = Image.create(608, 1080, false, Image.FORMAT_RGBA8)
	img.fill(Color(0.1, 0.2, 0.5))
	img.set_pixel(int(304 + sin(pos) * 200), 540, Color(1, 1, 0))
	var data = img.get_data()
	pipe.store_buffer(data)
	frame_count += 1
EOF
```

### 2. Create a minimal project.godot

```
cat > minimal_test/project.godot << 'EOF'
[application]
config/name="MinimalTest"
run/main_scene="res://test.gd"
[rendering]
renderer/rendering_method="forward_plus"
EOF
```

### 3. Run the pipe pipeline

```bash
export LIBVA_DRIVER_NAME=radeonsi
rm -f /tmp/test_pipe
mkfifo /tmp/test_pipe

# Start ffmpeg reader (VAAPI GPU encode)
timeout 30 ffmpeg -f rawvideo -pix_fmt rgba -s 608x1080 -framerate 25 \
  -i /tmp/test_pipe \
  -vf "format=nv12,hwupload" -vaapi_device /dev/dri/renderD128 \
  -c:v h264_vaapi -y minimal_output.mp4 &
FFPID=$!

# Start Godot writer
timeout 30 ~/.local/bin/godot4 --rendering-driver vulkan --display-driver headless \
  --path minimal_test

wait $FFPID 2>/dev/null
rm -f /tmp/test_pipe
```

### 4. Verify

```
ffprobe /tmp/minimal_output.mp4
echo "Exit code: $?"
```

### 5. If it works

Document the exact working pipeline in `recipe.md` for ag-04 to use.

### 6. If it fails

- Check the error message
- Fix the issue
- Repeat the test until it works
- Document the fix

## Output
- `recipe.md` — working minimal pipeline commands, or debugging steps if it failed
