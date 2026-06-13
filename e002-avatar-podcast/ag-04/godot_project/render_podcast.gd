extends Node

var config: Dictionary = {}
var segs: Array = []
var bg_texture: Texture2D
var avatar_a_texture: Texture2D
var avatar_b_texture: Texture2D

var bg_sprite: Sprite2D
var avatar_a: Sprite2D
var avatar_b: Sprite2D
var glow_a: ColorRect
var glow_b: ColorRect
var label_a: Label
var label_b: Label
var name_bg_a: ColorRect
var name_bg_b: ColorRect

var subtitle_label: Label
var subtitle_bg: ColorRect

var w := 608
var h := 1080
var fps := 25.0
var total_frames := 0
var duration := 0.0
var output_dir := "."
var current_speaker := ""

var project_dir := ""

var sub_chunks: Array = []
var sub_colors: Array = [
	Color(1, 1, 1),
	Color(1, 0.847, 0),
	Color(0, 1, 0.533),
	Color(1, 0.42, 0.42),
	Color(0.42, 0.737, 1),
]


func _ready() -> void:
	project_dir = ProjectSettings.globalize_path("res://")
	print("Project dir: ", project_dir)

	load_config()
	if not load_textures():
		get_tree().quit(1)
		return
	build_subtitle_chunks()
	setup_scene()

	Engine.max_fps = fps
	await get_tree().process_frame
	print("Starting render: ", total_frames, " frames at ", fps, " fps")

	var t_start = Time.get_ticks_msec()
	for i in range(total_frames):
		var t = i / fps
		update_scene(t)
		await get_tree().process_frame
		capture_frame(i)
		if i % 100 == 0 and i > 0:
			var elapsed = (Time.get_ticks_msec() - t_start) / 1000.0
			var rate = i / elapsed if elapsed > 0 else 0
			print(str(i), "/", total_frames, " frames (", rate, " fps)")

	var elapsed = (Time.get_ticks_msec() - t_start) / 1000.0
	print("Render complete: ", total_frames, " frames in ", elapsed, "s")
	get_tree().quit()


func load_config() -> void:
	var args = OS.get_cmdline_user_args()
	if args.is_empty():
		printerr("No config path provided")
		get_tree().quit(1)
		return

	var f = FileAccess.open(args[0], FileAccess.READ)
	if f == null:
		printerr("Cannot open config: ", args[0])
		get_tree().quit(1)
		return

	config = JSON.parse_string(f.get_as_text())
	if config == null or config.is_empty():
		printerr("Invalid config JSON")
		get_tree().quit(1)
		return

	segs = config.get("segments", [])
	duration = config.get("duration", 0.0)
	fps = config.get("fps", 25.0)
	w = config.get("w", 608)
	h = config.get("h", 1080)
	output_dir = config.get("output_dir", ".")
	total_frames = int(ceil(duration * fps))

	print("Config loaded: ", w, "x", h, ", ", total_frames, " frames")


func load_image_as_texture(path: String) -> Texture2D:
	var img = Image.new()
	var err = img.load(path)
	if err != OK:
		printerr("Failed to load image: ", path, " error: ", err)
		return null
	var tex = ImageTexture.create_from_image(img)
	return tex


func load_textures() -> bool:
	var bg_path = config.get("bg", "")
	var aa_path = config.get("avatar_a", "")
	var ab_path = config.get("avatar_b", "")

	if bg_path.begins_with("res://"):
		bg_path = bg_path.replace("res://", project_dir)
	if aa_path.begins_with("res://"):
		aa_path = aa_path.replace("res://", project_dir)
	if ab_path.begins_with("res://"):
		ab_path = ab_path.replace("res://", project_dir)

	print("Loading bg: ", bg_path)
	bg_texture = load_image_as_texture(bg_path)
	if bg_texture == null:
		printerr("Failed to load bg texture")
		return false

	avatar_a_texture = load_image_as_texture(aa_path)
	if avatar_a_texture == null:
		printerr("Failed to load avatar A texture")
		return false

	avatar_b_texture = load_image_as_texture(ab_path)
	if avatar_b_texture == null:
		printerr("Failed to load avatar B texture")
		return false

	print("Textures loaded successfully")
	return true


func build_subtitle_chunks() -> void:
	sub_chunks.clear()
	var color_idx := 0
	for seg in segs:
		var st = seg.get("start", 0.0) as float
		var et = seg.get("end", 0.0) as float
		var text: String = seg.get("text", "")
		var seg_dur = et - st
		if seg_dur <= 0 or text.is_empty():
			continue
		var words = text.split(" ", false)
		if words.is_empty():
			continue
		var chunks: Array[Array] = []
		var i := 0
		while i < words.size():
			var n = randi() % 3 + 2
			if n > words.size() - i:
				n = words.size() - i
			var chunk_words = words.slice(i, i + n)
			chunks.append(chunk_words)
			i += n
		var chunk_dur = seg_dur / chunks.size()
		for j in range(chunks.size()):
			var chunk_text = ""
			for w_i in range(chunks[j].size()):
				if w_i > 0:
					chunk_text += " "
				chunk_text += chunks[j][w_i]
			sub_chunks.append({
				"start": st + j * chunk_dur,
				"end": st + (j + 1) * chunk_dur,
				"text": chunk_text,
				"color": sub_colors[color_idx % sub_colors.size()],
			})
			color_idx += 1


func setup_scene() -> void:
	bg_sprite = Sprite2D.new()
	bg_sprite.texture = bg_texture
	bg_sprite.centered = false
	var crop_x = (bg_texture.get_width() - w) / 2
	bg_sprite.region_enabled = true
	bg_sprite.region_rect = Rect2(crop_x, 0, w, h)
	add_child(bg_sprite)

	var av_size := 188
	var glow_pad := 12
	var gap := 32
	var total_av_w := 2 * av_size + gap
	var av_x0 := (w - total_av_w) / 2
	var av_y := 124

	glow_a = ColorRect.new()
	glow_a.size = Vector2(av_size + glow_pad * 2, av_size + glow_pad * 2)
	glow_a.position = Vector2(av_x0 - glow_pad, av_y - glow_pad)
	glow_a.color = Color(0, 0, 0, 0)
	add_child(glow_a)

	avatar_a = Sprite2D.new()
	avatar_a.texture = avatar_a_texture
	var av_scale := av_size / float(avatar_a_texture.get_width())
	avatar_a.scale = Vector2(av_scale, av_scale)
	avatar_a.position = Vector2(av_x0 + av_size / 2, av_y + av_size / 2)
	add_child(avatar_a)

	name_bg_a = ColorRect.new()
	name_bg_a.size = Vector2(av_size + 20, 30)
	name_bg_a.position = Vector2(av_x0 - 10, av_y + av_size + 6)
	name_bg_a.color = Color(0, 0, 0, 0.6)
	add_child(name_bg_a)

	label_a = Label.new()
	label_a.text = "Gonzalo"
	label_a.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label_a.position = Vector2(av_x0, av_y + av_size + 6)
	label_a.size = Vector2(av_size + 20, 30)
	label_a.add_theme_color_override("font_color", Color(1, 1, 1))
	label_a.add_theme_font_size_override("font_size", 17)
	add_child(label_a)

	var b_x := av_x0 + av_size + gap

	glow_b = ColorRect.new()
	glow_b.size = Vector2(av_size + glow_pad * 2, av_size + glow_pad * 2)
	glow_b.position = Vector2(b_x - glow_pad, av_y - glow_pad)
	glow_b.color = Color(0, 0, 0, 0)
	add_child(glow_b)

	avatar_b = Sprite2D.new()
	avatar_b.texture = avatar_b_texture
	avatar_b.scale = Vector2(av_scale, av_scale)
	avatar_b.position = Vector2(b_x + av_size / 2, av_y + av_size / 2)
	add_child(avatar_b)

	name_bg_b = ColorRect.new()
	name_bg_b.size = Vector2(av_size + 20, 30)
	name_bg_b.position = Vector2(b_x - 10, av_y + av_size + 6)
	name_bg_b.color = Color(0, 0, 0, 0.6)
	add_child(name_bg_b)

	label_b = Label.new()
	label_b.text = "Salome"
	label_b.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label_b.position = Vector2(b_x, av_y + av_size + 6)
	label_b.size = Vector2(av_size + 20, 30)
	label_b.add_theme_color_override("font_color", Color(1, 1, 1))
	label_b.add_theme_font_size_override("font_size", 17)
	add_child(label_b)

	subtitle_bg = ColorRect.new()
	subtitle_bg.size = Vector2(w - 40, 50)
	subtitle_bg.position = Vector2(20, h - 50 - 50)
	subtitle_bg.color = Color(0, 0, 0, 0.5)
	add_child(subtitle_bg)

	subtitle_label = Label.new()
	subtitle_label.text = ""
	subtitle_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	subtitle_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	subtitle_label.position = Vector2(20, h - 50 - 50)
	subtitle_label.size = Vector2(w - 40, 50)
	subtitle_label.add_theme_font_size_override("font_size", 22)
	add_child(subtitle_label)

	update_scene(0.0)


func update_scene(t: float) -> void:
	var active := ""
	for seg in segs:
		var st = seg.get("start", 0.0) as float
		var et = seg.get("end", 0.0) as float
		if t >= st and t < et:
			active = seg.get("speaker", "")
			break

	current_speaker = active

	var a_dim := Color(0.6, 0.6, 0.6, 1.0)
	var b_dim := Color(0.6, 0.6, 0.6, 1.0)
	var a_full := Color(1.0, 1.0, 1.0, 1.0)
	var b_full := Color(1.0, 1.0, 1.0, 1.0)
	var a_name_col := Color(0.7, 0.7, 0.7, 1.0)
	var b_name_col := Color(0.7, 0.7, 0.7, 1.0)
	var a_glow := Color(0, 0, 0, 0)
	var b_glow := Color(0, 0, 0, 0)

	if active == "A":
		var pulse = 0.4 + 0.3 * sin(t * 4.0)
		a_glow = Color(0.0, 0.5, 1.0, pulse)
		a_dim = a_full
		a_name_col = Color(1.0, 1.0, 0.2, 1.0)
	elif active == "B":
		var pulse = 0.4 + 0.3 * sin(t * 4.0)
		b_glow = Color(1.0, 0.2, 0.6, pulse)
		b_dim = b_full
		b_name_col = Color(1.0, 1.0, 0.2, 1.0)

	avatar_a.modulate = a_dim
	avatar_b.modulate = b_dim
	glow_a.color = a_glow
	glow_b.color = b_glow
	label_a.add_theme_color_override("font_color", a_name_col)
	label_b.add_theme_color_override("font_color", b_name_col)

	var sub_text := ""
	var sub_color := Color(1, 1, 1)
	for chunk in sub_chunks:
		var cst = chunk["start"] as float
		var cet = chunk["end"] as float
		if t >= cst and t < cet:
			sub_text = chunk["text"]
			sub_color = chunk["color"]
			break
	subtitle_label.text = sub_text
	subtitle_label.add_theme_color_override("font_color", sub_color)
	subtitle_bg.visible = not sub_text.is_empty()


func capture_frame(i: int) -> void:
	var img = get_viewport().get_texture().get_image()
	if img == null:
		return
	var path = output_dir.path_join("frame_%05d.png" % i)
	img.save_png(path)
