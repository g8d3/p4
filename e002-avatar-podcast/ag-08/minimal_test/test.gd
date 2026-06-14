extends Node

var frame_count = 0
var target_frames = 50  # 2 seconds at 25fps
var pipe: FileAccess
var pos = 0.0

func _ready():
	pipe = FileAccess.open("res://frames.raw", FileAccess.WRITE)
	if pipe == null:
		printerr("FAIL: Cannot open frames.raw err=", FileAccess.get_open_error())
		get_tree().quit(1)
		return
	print("File opened OK")

func _process(delta):
	if frame_count >= target_frames:
		pipe.close()
		print("DONE: ", frame_count, " frames")
		get_tree().quit()
		return

	pos += 0.05
	var img = Image.create(608, 1080, false, Image.FORMAT_RGBA8)
	img.fill(Color(0.1, 0.2, 0.5))
	var cx = int(304 + sin(pos) * 200)
	img.set_pixel(cx, 540, Color(1, 1, 0))
	var data = img.get_data()
	pipe.store_buffer(data)
	frame_count += 1
