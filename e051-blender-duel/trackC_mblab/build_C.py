# Track C — MB-LAB (procedural humans): append 2 finalized chars, shared scene, L1 anim.
# Needs: charA.blend + charB.blend from gen_char.py
# Run: blender -b -P trackC_mblab/build_C.py
# Output: output/trackC.blend, trackC_*.png, trackC.mp4

import bpy, math, os, time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = "/home/vuos/code/p4/e051-blender-duel/output"
os.makedirs(OUT, exist_ok=True)
t_all = time.time()

# ---- 1. clean + shared scene (identical to Tracks A/B) ----------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
t0 = time.time()
S = bpy.context.scene
S.render.engine = 'BLENDER_EEVEE'
S.render.resolution_x, S.render.resolution_y = 1280, 720
S.render.resolution_percentage = int(os.environ.get("RES_PCT", "50"))
STILLS_ONLY = os.environ.get("STILLS_ONLY", "") == "1"
S.render.film_transparent = False
S.render.fps = 24
S.frame_start, S.frame_end = 1, 144
S.eevee.taa_render_samples = 8
S.world.use_nodes = True
S.world.node_tree.nodes["Background"].inputs[0].default_value = (0.08, 0.09, 0.12, 1)
bpy.ops.object.camera_add(location=(0, -7.0, 2.6), rotation=(1.39, 0, 0))
S.camera = bpy.context.object
bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
bpy.context.object.data.energy = 5.0
bpy.ops.object.light_add(type='AREA', location=(0, -4, 4), rotation=(0.6, 0, 0))
bpy.context.object.data.energy = 600.0
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

# ---- 2. append finalized MB-Lab characters ----------------------------------
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
            pass  # already linked
    return mesh, rig

meshA, rigA = load_char(os.path.join(HERE, "charA.blend"))
meshB, rigB = load_char(os.path.join(HERE, "charB.blend"))

PEOPLE = [
    {"prefix": "A", "mesh": meshA, "rig": rigA, "x": -1.2, "rot": 0.78, "ph": 0.0},
    {"prefix": "B", "mesh": meshB, "rig": rigB, "x": 1.2, "rot": -0.78, "ph": 1.7},
]
# MB-Lab skin shader: kill SSS (EEVEE cost + darkening), keep base color
for P in PEOPLE:
    for m in P["mesh"].data.materials:
        if m and m.use_nodes:
            bsdf = m.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                try:
                    bsdf.inputs["Subsurface"].default_value = 0.0
                except KeyError:
                    pass
for P in PEOPLE:
    P["rig"].location = (P["x"], 0, 0)
    P["rig"].rotation_euler[2] = P["rot"]
    # jaw shape key: prefer mouthOpen, fallback to anything mouth-ish
    keys = P["mesh"].data.shape_keys.key_blocks.keys() if P["mesh"].data.shape_keys else []
    pref = ["mouthopen_max", "mouthopen", "jawout_max", "mouthchew_max", "mouthhalf_max"]
    low = {k.lower(): k for k in keys}
    P["jawkey"] = next((low[c] for c in ["expressions_" + p for p in pref] if c in low), None)
    if P["jawkey"] is None:
        cands = [k for k in keys if "mouth" in k.lower() and "max" in k.lower()]
        P["jawkey"] = cands[0] if cands else None
    print("char %s: jawkey=%s arms=%s" % (
        P["prefix"], P["jawkey"],
        [b.name for b in P["rig"].pose.bones if "upperarm" in b.name.lower()]))
t_model = time.time() - t0

# ---- 3. rig: none needed (MB-Lab ships rigged) — just verify -----------------
t0 = time.time()
for P in PEOPLE:
    assert P["rig"] and P["jawkey"], "missing rig or jaw key for %s" % P["prefix"]
t_rig = time.time() - t0

# ---- 4. L1 animation: jaw shape key + head/arm sine loop ---------------------
t0 = time.time()
def turn(prefix, f):
    return (1.0 if f <= 72 else 0.12) if prefix == "A" else (1.0 if f > 72 else 0.12)

for P in PEOPLE:
    rig, mesh = P["rig"], P["mesh"]
    kb = mesh.data.shape_keys.key_blocks[P["jawkey"]]
    armL = next((b.name for b in rig.pose.bones if b.name.lower() == "upperarm_l"), None)
    armR = next((b.name for b in rig.pose.bones if b.name.lower() == "upperarm_r"), None)
    for f in range(1, 145, 4):
        S.frame_set(f)
        e = turn(P["prefix"], f)
        kb.value = abs(math.sin(f * 0.45 + P["ph"])) * 0.9 * e
        kb.keyframe_insert(data_path="value", frame=f)
        head = rig.pose.bones.get("head")
        if head:
            head.rotation_mode = 'XYZ'
            head.rotation_euler[0] = math.sin(f * 0.12 + P["ph"]) * 0.10 * e
            head.keyframe_insert(data_path="rotation_euler")
        for bb, s in ((armL, 1), (armR, -1)):
            if bb:
                rb = rig.pose.bones[bb]
                rb.rotation_mode = 'XYZ'
                rb.rotation_euler[1] = s * (0.15 + abs(math.sin(f * 0.2 + P["ph"])) * 0.35 * e)
                rb.keyframe_insert(data_path="rotation_euler")
t_anim = time.time() - t0

# ---- 5. save + render ---------------------------------------------------------
t0 = time.time()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "trackC.blend"))
S.render.image_settings.file_format = 'PNG'
stills = [("trackC_f36", 36)] if STILLS_ONLY else (
    ("trackC_f01", 1), ("trackC_f36", 36), ("trackC_f108", 108))
for name, fr in stills:
    S.frame_set(fr)
    S.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
if STILLS_ONLY:
    print("TRACK-C STILLS-ONLY DONE")
else:
    S.render.image_settings.file_format = 'FFMPEG'
    S.render.ffmpeg.format = 'MPEG4'
    S.render.ffmpeg.codec = 'H264'
    S.render.filepath = os.path.join(OUT, "trackC.mp4")
    bpy.ops.render.render(animation=True)
t_render = time.time() - t0

print("\nTRACK-C TIMINGS  model=%.1fs rig=%.1fs anim=%.1fs render=%.1fs total=%.1fs"
      % (t_model, t_rig, t_anim, t_render, time.time() - t_all))
print("TRACK-C DONE:", os.path.join(OUT, "trackC.mp4"))
