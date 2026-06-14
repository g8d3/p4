extends Node

var frame_count = 0
var target_frames = 50  # 2 seconds at 25fps
var pipe: FileAccess
var pos = 0.0

func _ready():
	var pipe_path = ProjectSettings.globalize_path("res://test_pipe")
	pipe = FileAccess.open(pipe_path, FileAccess.WRITE)
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
