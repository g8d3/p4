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
var duration := 0.0
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

var elapsed := 0.0
var start_time := 0
var frame_count := 0

var pipe_file: FileAccess
var pipe_path := ""
var raw_path := ""
var resume_offset := 0.0


func _ready() -> void:
	project_dir = ProjectSettings.globalize_path("res://")
	print("Project dir: ", project_dir)

	load_config()
	if not load_textures():
		get_tree().quit(1)
		return
	build_subtitle_chunks()
	setup_scene()

	raw_path = project_dir + "../frames.raw"
	var frame_bytes := w * h * 4
	var resume_frame := 0

	if FileAccess.file_exists(raw_path):
		var existing = FileAccess.open(raw_path, FileAccess.READ)
		if existing != null:
			var fsize = existing.get_length()
			existing.close()
			resume_frame = fsize / frame_bytes
			print("Existing frames.raw: ", fsize, " bytes = ", resume_frame, " frames done")

	if resume_frame > 0:
		pipe_file = FileAccess.open(raw_path, FileAccess.READ_WRITE)
		if pipe_file != null:
			pipe_file.seek_end()
	else:
		pipe_file = FileAccess.open(raw_path, FileAccess.WRITE)
	if pipe_file == null:
		printerr("Cannot open output file: ", raw_path)
		get_tree().quit(1)
		return

	var total_frames := int(duration * fps)
	var remaining := total_frames - resume_frame
	print("Output file opened: ", raw_path, " (", w, "x", h, " RGBA @ ", fps, " fps, ", duration, "s = ", total_frames, " frames)")
	print("Resuming from frame ", resume_frame, "/", total_frames, " (", remaining, " remaining)")

	frame_count = resume_frame
	resume_offset = resume_frame / fps
	Engine.max_fps = fps
	start_time = Time.get_ticks_msec()
	print("Starting render: ", duration, "s at ", fps, " fps from frame ", resume_frame)


func _process(_delta: float) -> void:
	elapsed = resume_offset + (Time.get_ticks_msec() - start_time) / 1000.0
	var target_frames = int(duration * fps)
	if frame_count >= target_frames:
		print("Render complete: ", frame_count, " frames")
		get_tree().quit()
		return

	update_scene(elapsed)

	var img = get_viewport().get_texture().get_image()
	if img != null:
		var data = img.get_data()
		if data != null:
			pipe_file.store_buffer(data)
	frame_count += 1


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

	print("Config loaded: ", w, "x", h, ", ", duration, "s")


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


func _split_into_chunks(words: Array, max_chunks: int, max_per_chunk: int) -> Array:
	var result: Array = []
	var i := 0
	while i < words.size() and result.size() < max_chunks:
		var remaining_chunks = max_chunks - result.size()
		var remaining_words = words.size() - i
		var target_size = int(ceil(float(remaining_words) / remaining_chunks))
		target_size = mini(target_size, max_per_chunk)

		var end = i + target_size
		if end >= words.size():
			end = words.size()
		else:
			for j in range(end, i, -1):
				var w = words[j - 1]
				if w.ends_with(",") or w.ends_with(".") or w.ends_with("?") or w.ends_with("!") or w.ends_with(":") or w.ends_with(";"):
					end = j
					break

		var chunk = words.slice(i, end)
		if not chunk.is_empty():
			result.append(chunk)
		i = end

	if i < words.size():
		if result.size() < max_chunks:
			result.append(words.slice(i))
		else:
			result[-1] += words.slice(i)

	return result


func _split_into_n_parts(words: Array, n: int) -> Array:
	var result: Array = []
	var actual_n = mini(n, words.size())
	if actual_n <= 0:
		return [words]
	var base = words.size() / actual_n
	var extra = words.size() % actual_n
	var start := 0
	for i in range(actual_n):
		var chunk_size = base + (1 if i < extra else 0)
		result.append(words.slice(start, start + chunk_size))
		start += chunk_size
	return result


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

		var num_words = words.size()
		var max_chunks := 1
		var max_per_chunk := 5
		if num_words <= 4:
			max_chunks = 1
			max_per_chunk = 4
		elif num_words <= 10:
			max_chunks = 2
		elif num_words <= 15:
			max_chunks = 3
		elif num_words <= 20:
			max_chunks = 4
		else:
			max_chunks = 5

		var chunks = _split_into_chunks(words, max_chunks, max_per_chunk)
		var chunk_dur = seg_dur / chunks.size()

		for j in range(chunks.size()):
			var chunk_text = " ".join(chunks[j])
			var chunk_start = st + j * chunk_dur
			var chunk_end = st + (j + 1) * chunk_dur
			var display_dur = chunk_end - chunk_start

			if display_dur < 1.2:
				chunk_end = chunk_start + 1.2
				display_dur = 1.2

			if display_dur > 3.0:
				var num_sub = int(ceil(display_dur / 3.0))
				var sub_chunk_dur = display_dur / num_sub
				var sub_words = _split_into_n_parts(chunks[j], num_sub)
				for k in range(sub_words.size()):
					var sub_text = " ".join(sub_words[k])
					sub_chunks.append({
						"start": chunk_start + k * sub_chunk_dur,
						"end": chunk_start + (k + 1) * sub_chunk_dur,
						"text": sub_text,
						"color": sub_colors[color_idx % sub_colors.size()],
					})
					color_idx += 1
			else:
				sub_chunks.append({
					"start": chunk_start,
					"end": chunk_end,
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
	subtitle_bg.position = Vector2(20, h - 60 - 50)
	subtitle_bg.color = Color(0, 0, 0, 0.5)
	add_child(subtitle_bg)

	subtitle_label = Label.new()
	subtitle_label.text = ""
	subtitle_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	subtitle_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	subtitle_label.position = Vector2(20, h - 60 - 50)
	subtitle_label.size = Vector2(w - 40, 50)
	subtitle_label.add_theme_font_size_override("font_size", 18)
	subtitle_label.add_theme_font_override("font", ThemeDB.fallback_font)
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
