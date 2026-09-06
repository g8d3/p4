# Track E — MPFB2 (procedural humans): append 2 generated chars, shared scene, L1 anim.
# Needs: charA.blend (female) + charB.blend (male) from gen_char.py
# Run: blender -b -P trackR3_mpfb/build_E.py
# Output: output/trackR3.blend, trackR3_*.png, trackR3.mp4

import bpy, math, os, time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = "/home/vuos/code/p4/e051-blender-duel/trackR3_blendergen/output"
os.makedirs(OUT, exist_ok=True)
t_all = time.time()

# ---- 1. clean ---------------------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
t0 = time.time()

# ---- 2. shared scene (VERBATIM from trackA_procedural/build_A.py) ------------
S = bpy.context.scene
S.render.engine = 'BLENDER_EEVEE'
S.render.resolution_x, S.render.resolution_y = 1280, 720
S.render.resolution_percentage = int(os.environ.get("RES_PCT", "50"))
STILLS_ONLY = os.environ.get("STILLS_ONLY", "") == "1"
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

def flat_mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1)
    return m

BODY_A = flat_mat("BodyA", (0.75, 0.22, 0.2))  # red = speaker A (same code as track A)
BODY_B = flat_mat("BodyB", (0.2, 0.4, 0.8))    # blue = speaker B
t_scene = time.time() - t0

# ---- 3. append MPFB characters ----------------------------------------------
t0 = time.time()
def load_char(path):
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = list(src.objects)
    mesh = max([o for o in dst.objects if o.type == 'MESH'],
               key=lambda o: len(o.data.polygons))
    rig = max([o for o in dst.objects if o.type == 'ARMATURE'],
              key=lambda o: len(o.data.bones))
    for o in (mesh, rig):
        try:
            S.collection.objects.link(o)
        except RuntimeError:
            pass
    return mesh, rig

meshA, rigA = load_char(os.path.join(HERE, "charA.blend"))
meshB, rigB = load_char(os.path.join(HERE, "charB.blend"))

PEOPLE = [
    {"prefix": "A", "mesh": meshA, "rig": rigA, "x": -1.2, "rot": 0.25, "ph": 0.0, "mat": BODY_A},
    {"prefix": "B", "mesh": meshB, "rig": rigB, "x": 1.2, "rot": -0.25, "ph": 1.7, "mat": BODY_B},
]
for P in PEOPLE:
    P["mesh"].data.materials.clear()
    P["mesh"].data.materials.append(P["mat"])
    P["rig"].location = (P["x"], 0, 0.03)
    P["rig"].rotation_euler[2] = P["rot"]
    assert "jaw" in P["rig"].data.bones and "head" in P["rig"].data.bones
    print("char %s: verts=%d bones=%d" % (P["prefix"], len(P["mesh"].data.vertices), len(P["rig"].data.bones)))
t_model = time.time() - t0

# ---- 4. rig: none needed (MPFB ships rigged + weighted) -----------------------
t0 = time.time()
t_rig = time.time() - t0

# ---- 5. L1 animation: jaw-bone flap + head bob + arm gestures ----------------
JAW_SIGN = float(os.environ.get("JAW_SIGN", "-1.0"))  # jaw local-X open direction
t0 = time.time()
def turn(prefix, f):
    if prefix == "A":
        return 1.0 if f <= 72 else 0.12
    return 1.0 if f > 72 else 0.12

for P in PEOPLE:
    rig = P["rig"]
    jaw = rig.pose.bones["jaw"]
    head = rig.pose.bones["head"]
    arms = [b.name for b in rig.pose.bones]
    armL = next((n for n in arms if "upperarm01" in n and n.endswith(".L")), None)
    armR = next((n for n in arms if "upperarm01" in n and n.endswith(".R")), None)
    for f in range(1, 145, 4):
        S.frame_set(f)
        e = turn(P["prefix"], f)
        jaw.rotation_mode = 'XYZ'
        jaw.rotation_euler[0] = JAW_SIGN * abs(math.sin(f * 0.45 + P["ph"])) * 0.35 * e
        jaw.keyframe_insert(data_path="rotation_euler")
        head.rotation_mode = 'XYZ'
        head.rotation_euler[0] = math.sin(f * 0.12 + P["ph"]) * 0.08 * e
        head.keyframe_insert(data_path="rotation_euler")
        for bb, s in ((armL, 1), (armR, -1)):
            if bb:
                rb = rig.pose.bones[bb]
                rb.rotation_mode = 'XYZ'
                rb.rotation_euler[1] = s * (0.15 + abs(math.sin(f * 0.2 + P["ph"])) * 0.35 * e)
                rb.keyframe_insert(data_path="rotation_euler")
t_anim = time.time() - t0

# ---- 6. save + render ---------------------------------------------------------
t0 = time.time()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "trackR3.blend"))
S.render.image_settings.file_format = 'PNG'
stills = [("trackR3_f36", 36)] if STILLS_ONLY else (
    ("trackR3_f01", 1), ("trackR3_f36", 36), ("trackR3_f108", 108))
for name, fr in stills:
    S.frame_set(fr)
    S.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
if STILLS_ONLY:
    print("TRACK-R3 STILLS-ONLY DONE")
else:
    S.render.image_settings.file_format = 'FFMPEG'
    S.render.ffmpeg.format = 'MPEG4'
    S.render.ffmpeg.codec = 'H264'
    S.render.filepath = os.path.join(OUT, "trackR3.mp4")
    bpy.ops.render.render(animation=True)
t_render = time.time() - t0

print("\nTRACK-R3 TIMINGS  model=%.1fs rig=%.1fs anim=%.1fs render=%.1fs total=%.1fs"
      % (t_model, t_rig, t_anim, t_render, time.time() - t_all))
print("TRACK-R3 DONE:", os.path.join(OUT, "trackR3.mp4"))
