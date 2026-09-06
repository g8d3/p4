# Track A — PROCEDURAL: parametric bodies + Rigify Human Meta-Rig + computed talk loop.
# Run: blender -b -P trackA_procedural/build_A.py
# Output: output/trackA.blend, trackA_*.png stills, trackA.mp4

import bpy, math, os, time

OUT = "/home/vuos/code/p4/e051-blender-duel/output"
os.makedirs(OUT, exist_ok=True)
t_all = time.time()

# ---- 1. clean ---------------------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
t0 = time.time()

# ---- 2. shared scene (identical in both tracks) -----------------------------
S = bpy.context.scene
S.render.engine = 'BLENDER_EEVEE'
S.render.resolution_x, S.render.resolution_y = 1280, 720
S.render.resolution_percentage = 50
S.render.film_transparent = False
S.render.fps = 24
S.frame_start, S.frame_end = 1, 144
S.eevee.taa_render_samples = 16
S.world.use_nodes = True
S.world.node_tree.nodes["Background"].inputs[0].default_value = (0.08, 0.09, 0.12, 1)

bpy.ops.object.camera_add(location=(0, -7.0, 2.6), rotation=(1.39, 0, 0))
S.camera = bpy.context.object
bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
bpy.context.object.data.energy = 3.0
bpy.ops.object.light_add(type='AREA', location=(0, -4, 4), rotation=(0.6, 0, 0))
bpy.context.object.data.energy = 200.0
bpy.context.object.data.size = 4.0
bpy.ops.object.light_add(type='AREA', location=(0, -6, 5), rotation=(0.35, 0, 0))
bpy.context.object.data.energy = 1200.0
bpy.context.object.data.size = 3.0
S.view_settings.exposure = 0.5
bpy.ops.mesh.primitive_plane_add(size=30)
ground = bpy.context.object
gm = bpy.data.materials.new("Ground")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.16, 0.17, 0.2, 1)
ground.data.materials.append(gm)

def mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1)
    return m

BODY_A = mat("BodyA", (0.75, 0.22, 0.2))
BODY_B = mat("BodyB", (0.2, 0.4, 0.8))
WHITE = mat("White", (0.95, 0.95, 0.95))
DARK = mat("DarkJaw", (0.1, 0.05, 0.05))
t_scene = time.time() - t0

# ---- 3. parametric person: one PARTS table drives both characters -----------
t0 = time.time()
# (kind, size, offset-from-feet, material-key, join-into-body?)
PARTS = [
    ("cube", (0.6, 0.4, 0.8), (0, 0, 1.2), "body", True),    # torso
    ("sphere", 0.35, (0, 0, 2.2), "body", True),             # head
    ("sphere", 0.06, (-0.13, -0.3, 2.28), "white", False),   # eye L
    ("sphere", 0.06, (0.13, -0.3, 2.28), "white", False),    # eye R
    ("cube", (0.25, 0.1, 0.12), (0, -0.28, 2.0), "dark", False),  # jaw
    ("cyl", (0.09, 0.9), (-0.45, 0, 1.3), "body", True),     # arm L
    ("cyl", (0.09, 0.9), (0.45, 0, 1.3), "body", True),      # arm R
    ("cyl", (0.11, 0.9), (-0.2, 0, 0.45), "body", True),     # leg L
    ("cyl", (0.11, 0.9), (0.2, 0, 0.45), "body", True),      # leg R
]
MATKEY = {"body": None, "white": WHITE, "dark": DARK}  # body filled per person

def make_person(prefix, x, body_mat, rot_z):
    MATKEY["body"] = body_mat
    made = []
    for i, (kind, p, off, mk, join) in enumerate(PARTS):
        ox, oy, oz = off
        if kind == "cube":
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x + ox, oy, oz))
            o = bpy.context.object
            o.scale = (p[0], p[1], p[2])
        elif kind == "sphere":
            bpy.ops.mesh.primitive_uv_sphere_add(radius=p, location=(x + ox, oy, oz))
            o = bpy.context.object
        else:
            bpy.ops.mesh.primitive_cylinder_add(radius=p[0], depth=p[1], location=(x + ox, oy, oz))
            o = bpy.context.object
        o.name = "%s_part%02d" % (prefix, i)
        o.data.materials.append(MATKEY[mk])
        o.rotation_euler[2] = rot_z
        made.append((o, join))
    # join deformable parts into one mesh for auto-weighting
    bpy.ops.object.select_all(action='DESELECT')
    for o, join in made:
        if join:
            o.select_set(True)
    bpy.context.view_layer.objects.active = [o for o, j in made if j][0]
    bpy.ops.object.join()
    body = bpy.context.object
    body.name = prefix + "_Body"
    by_idx = {int(o.name[-2:]): o for o, j in made if not j}
    return {"prefix": prefix, "x": x, "body": body, "head": None,
            "eyeL": by_idx[2], "eyeR": by_idx[3], "jaw": by_idx[4]}

PEOPLE = [make_person("A", -1.2, BODY_A, 0.25),
          make_person("B", 1.2, BODY_B, -0.25)]
t_model = time.time() - t0

# ---- 4. rig: Rigify Human Meta-Rig (ships with Blender = widely known) ------
t0 = time.time()
import addon_utils
addon_utils.enable('rigify', default_set=True)
bpy.ops.preferences.addon_enable(module='rigify')
print('rigify metarig_add present:', hasattr(bpy.ops.object, 'armature_human_metarig_add'))

for P in PEOPLE:
    try:
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.object.armature_human_metarig_add()  # Blender 4.x name
        rig = bpy.context.object
        rig.name = P["prefix"] + "_RIG"
        rig.location = (P["x"], 0, 0.1)
        bpy.context.view_layer.update()
        bpy.ops.object.select_all(action='DESELECT')
        P["body"].select_set(True)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        P["rig"] = rig
        print("rig %s: %d bones" % (P["prefix"], len(rig.data.bones)))
    except Exception as e:
        print("meta-rig failed for %s: %s" % (P["prefix"], e))
        P["rig"] = None
t_rig = time.time() - t0

def find_bone(rig, *cands):
    if rig is None:
        return None
    for b in rig.pose.bones:
        n = b.name.lower()
        if any(c in n for c in cands):
            return b.name
    return None

# ---- 5. animation: computed sine loop, zero acting choices ------------------
t0 = time.time()
JAW_BASE = {P["prefix"]: P["jaw"].location.z for P in PEOPLE}

def turn(prefix, f):
    if prefix == "A":
        return 1.0 if f <= 72 else 0.12
    return 1.0 if f > 72 else 0.12

for P in PEOPLE:
    rig = P["rig"]
    head_b = find_bone(rig, "head")
    arms = [b.name for b in rig.pose.bones] if rig else []
    armL = next((n for n in arms if "upper_arm" in n and n.endswith(".L")), None)
    armR = next((n for n in arms if "upper_arm" in n and n.endswith(".R")), None)
    if armL is None:
        armL = next((n for n in arms if n.endswith(".L") and ("arm" in n or "shoulder" in n)), None)
    if armR is None:
        armR = next((n for n in arms if n.endswith(".R") and ("arm" in n or "shoulder" in n)), None)
    ph = 0.0 if P["prefix"] == "A" else 1.7
    for f in range(1, 145, 4):
        S.frame_set(f)
        e = turn(P["prefix"], f)
        P["jaw"].location.z = JAW_BASE[P["prefix"]] - abs(math.sin(f * 0.45 + ph)) * 0.09 * e
        P["jaw"].keyframe_insert(data_path="location", index=2)
        if rig is not None:
            if head_b:
                rb = rig.pose.bones[head_b]
                rb.rotation_mode = 'XYZ'
                rb.rotation_euler[0] = math.sin(f * 0.12 + ph) * 0.12 * e
                rb.rotation_euler[2] = math.sin(f * 0.07 + ph) * 0.1
                rb.keyframe_insert(data_path="rotation_euler")
            for bb, s in ((armL, 1), (armR, -1)):
                if bb:
                    rb = rig.pose.bones[bb]
                    rb.rotation_mode = 'XYZ'
                    rb.rotation_euler[1] = s * (0.25 + abs(math.sin(f * 0.2 + ph)) * 0.45 * e)
                    rb.keyframe_insert(data_path="rotation_euler")
    for f in list(range(20, 145, 41)) + list(range(38, 145, 41)):
        for eye in (P["eyeL"], P["eyeR"]):
            S.frame_set(f)
            eye.scale.y = 0.15
            eye.keyframe_insert(data_path="scale", index=1)
            S.frame_set(min(f + 2, 144))
            eye.scale.y = 1.0
            eye.keyframe_insert(data_path="scale", index=1)
    if rig is not None:  # whole-body sway: shot reads even if bone names missed
        for f in range(1, 145, 12):
            S.frame_set(f)
            rig.rotation_euler[2] = math.sin(f * 0.1 + ph) * 0.03
            rig.keyframe_insert(data_path="rotation_euler", index=2)
t_anim = time.time() - t0

# ---- 6. save + render --------------------------------------------------------
t0 = time.time()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "trackA.blend"))
S.render.image_settings.file_format = 'PNG'
for name, fr in (("trackA_f01", 1), ("trackA_f36", 36), ("trackA_f108", 108)):
    S.frame_set(fr)
    S.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
S.render.image_settings.file_format = 'FFMPEG'
S.render.ffmpeg.format = 'MPEG4'
S.render.ffmpeg.codec = 'H264'
S.render.filepath = os.path.join(OUT, "trackA.mp4")
bpy.ops.render.render(animation=True)
t_render = time.time() - t0

print("\nTRACK-A TIMINGS  model=%.1fs rig=%.1fs anim=%.1fs render=%.1fs total=%.1fs"
      % (t_model, t_rig, t_anim, t_render, time.time() - t_all))
print("TRACK-A DONE:", os.path.join(OUT, "trackA.mp4"))
