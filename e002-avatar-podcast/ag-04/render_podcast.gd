extends SceneTree

const FPS := 25
const W := 1920
const H := 1080

var timing: Array
var total_frames: int

func _init():
	var output_dir = "frames"
	var dir = DirAccess.open("res://")
	if dir:
		dir.make_dir_recursive(output_dir)

	var bg_img = Image.load_from_file("../ag-06/podcast_bg.png")
	var aa_img = Image.load_from_file("../ag-06/avatar_a.png")
	var ab_img = Image.load_from_file("../ag-06/avatar_b.png")

	var bg_tex = ImageTexture.create_from_image(bg_img)
	var aa_tex = ImageTexture.create_from_image(aa_img)
	var ab_tex = ImageTexture.create_from_image(ab_img)

	var bg = Sprite2D.new()
	bg.texture = bg_tex
	bg.position = Vector2(W / 2, H / 2)

	var aa = Sprite2D.new()
	aa.texture = aa_tex
	aa.position = Vector2(480, 540)

	var ab = Sprite2D.new()
	ab.texture = ab_tex
	ab.position = Vector2(1440, 540)

	var root = get_root()
	root.add_child(bg)
	root.add_child(aa)
	root.add_child(ab)

	var file = FileAccess.open("../ag-03/timing.json", FileAccess.READ)
	var json = JSON.new()
	json.parse(file.get_as_text())
	timing = json.data

	var total_dur = 0.0
	for s in timing:
		total_dur += s["duration"]
	total_frames = int(ceil(total_dur * FPS))

	root.size = Vector2i(W, H)
	root.transparent_bg = false

	print("Rendering %d frames..." % total_frames)
	RenderingServer.set_default_clear_color(Color.BLACK)

	for f in range(total_frames):
		var t = f / float(FPS)
		var cum = 0.0
		var speaker = ""
		for s in timing:
			cum += s["duration"]
			if t < cum:
				speaker = s["speaker"]
				break

		var bounce = 1.0 + 0.03 * sin(t * 10.0)
		if speaker == "A":
			aa.scale = Vector2(bounce, bounce)
			ab.scale = Vector2.ONE
		elif speaker == "B":
			aa.scale = Vector2.ONE
			ab.scale = Vector2(bounce, bounce)
		else:
			aa.scale = Vector2.ONE
			ab.scale = Vector2.ONE

		RenderingServer.force_draw()
		var img = root.get_texture().get_image()
		img.save_png(output_dir + "/frame_%05d.png" % [f + 1])

		if (f + 1) % 100 == 0:
			print("Frame %d/%d" % [f + 1, total_frames])

	print("Done! Rendered %d frames." % total_frames)
	quit()
