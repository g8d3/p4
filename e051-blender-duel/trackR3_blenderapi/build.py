# Track R3 blender-api — talking duo, 6 s @24 fps L1.
# Proven fast pattern from trackB_scratch/build_B.py: capsules + 5-bone rigs + hand keys.
# Scene block COPIED VERBATIM from trackA_procedural/build_A.py (do not reinvent).
# Run: blender -b -P trackR3_blenderapi/build.py
# Env: STILLS_ONLY=1 (skip mp4), ONLY_F36=1 (blend + f36 still only, fastest viable)
# Output (all in this dir): R3blendapi.blend, R3blendapi_*.png, R3blendapi.mp4

import bpy, os, time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE
os.makedirs(OUT, exist_ok=True)
STILLS_ONLY = os.environ.get("STILLS_ONLY", "") == "1"
ONLY_F36 = os.environ.get("ONLY_F36", "") == "1"
t_all = time.time()

# ---- 1. clean ---------------------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
t0 = time.time()

# ---- 2. shared scene (identical to Track A) ---------------------------------
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

# ---- 3. bodies, placed piece by piece ---------------------------------------
t0 = time.time()
def block(name, op, kwargs, scale, loc, rot_z, material):
    op(location=loc, **kwargs)
    o = bpy.context.object
    o.name = name
    if scale:
        o.scale = scale
    o.rotation_euler[2] = rot_z
    o.data.materials.append(material)
    return o

def make_person(prefix, x, body_mat, rot_z):
    torso = block(prefix + "_torso", bpy.ops.mesh.primitive_cube_add, {"size": 1},
                  (0.6, 0.4, 0.8), (x, 0, 1.2), rot_z, body_mat)
    head = block(prefix + "_head", bpy.ops.mesh.primitive_uv_sphere_add, {"radius": 0.35},
                 None, (x, 0, 2.2), rot_z, body_mat)
    eyeL = block(prefix + "_eyeL", bpy.ops.mesh.primitive_uv_sphere_add, {"radius": 0.06},
                 None, (x - 0.13, -0.3, 2.28), 0.0, WHITE)
    eyeR = block(prefix + "_eyeR", bpy.ops.mesh.primitive_uv_sphere_add, {"radius": 0.06},
                 None, (x + 0.13, -0.3, 2.28), 0.0, WHITE)
    jaw = block(prefix + "_jaw", bpy.ops.mesh.primitive_cube_add, {"size": 1},
                (0.25, 0.1, 0.12), (x, -0.28, 2.0), rot_z, DARK)
    armL = block(prefix + "_armL", bpy.ops.mesh.primitive_cylinder_add, {"radius": 0.09, "depth": 0.9},
                 None, (x - 0.45, 0, 1.3), 0.0, body_mat)
    armR = block(prefix + "_armR", bpy.ops.mesh.primitive_cylinder_add, {"radius": 0.09, "depth": 0.9},
                 None, (x + 0.45, 0, 1.3), 0.0, body_mat)
    legL = block(prefix + "_legL", bpy.ops.mesh.primitive_cylinder_add, {"radius": 0.11, "depth": 0.9},
                 None, (x - 0.2, 0, 0.45), 0.0, body_mat)
    legR = block(prefix + "_legR", bpy.ops.mesh.primitive_cylinder_add, {"radius": 0.11, "depth": 0.9},
                 None, (x + 0.2, 0, 0.45), 0.0, body_mat)
    bpy.ops.object.select_all(action='DESELECT')
    for o in (torso, head, eyeL, eyeR, jaw, armL, armR, legL, legR):
        o.select_set(True)
    bpy.context.view_layer.objects.active = torso
    bpy.ops.object.join()
    body = bpy.context.object
    body.name = prefix + "_Body"
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return {"prefix": prefix, "x": x, "body": body}

PEOPLE = [make_person("A", -1.2, BODY_A, 0.25),
          make_person("B", 1.2, BODY_B, -0.25)]
t_model = time.time() - t0

# ---- 4. rig: custom 5-bone armature, one bone at a time ----------------------
t0 = time.time()
def make_rig(P):
    x = P["x"]
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.armature_add(enter_editmode=True, location=(x, 0, 0))
    arm = bpy.context.object
    arm.name = P["prefix"] + "_RIG"
    eb = arm.data.edit_bones
    spine = eb[0]
    spine.name = "Spine"
    spine.head, spine.tail = (0, 0, 0.7), (0, 0, 1.6)
    head = eb.new("Head")
    head.head, head.tail = (0, 0, 1.6), (0, 0, 2.35)
    head.parent = spine
    jawb = eb.new("JawB")
    jawb.head, jawb.tail = (0, -0.25, 2.05), (0, -0.25, 1.9)
    jawb.parent = head
    armL = eb.new("ArmL")
    armL.head, armL.tail = (0.35, 0, 1.55), (0.65, 0, 0.95)
    armL.parent = spine
    armR = eb.new("ArmR")
    armR.head, armR.tail = (-0.35, 0, 1.55), (-0.65, 0, 0.95)
    armR.parent = spine
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    P["body"].select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    P["rig"] = arm

for P in PEOPLE:
    make_rig(P)
t_rig = time.time() - t0

# ---- 5. animation: hand-acted to the fake dialogue --------------------------
# A (1-72):  "HEY! did the pro-CED-u-ral RIG save TIME?"
# B (73-144): "YES! but LOOK at my HANDS!"
t0 = time.time()
def key_bone(arm, bone, f, rx=0.0, ry=0.0, rz=0.0):
    S.frame_set(f)
    pb = arm.pose.bones[bone]
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = (rx, ry, rz)
    pb.keyframe_insert(data_path="rotation_euler")

A = PEOPLE[0]
B = PEOPLE[1]

A_JAW = [(1, 0.0), (5, 0.55), (9, 0.1), (13, 0.45), (17, 0.05), (21, 0.4),
         (25, 0.15), (29, 0.6), (33, 0.1), (37, 0.4), (41, 0.0), (45, 0.5),
         (49, 0.2), (53, 0.45), (57, 0.05), (61, 0.35), (65, 0.1),
         (69, 0.25), (72, 0.0)]
for f, v in A_JAW:
    key_bone(A["rig"], "JawB", f, rx=v)
for f, rx, rz in [(1, 0, 0), (5, 0.12, 0.03), (12, -0.04, 0),
                  (29, 0.12, -0.03), (40, -0.03, 0), (61, 0.12, 0.03), (72, 0, 0)]:
    key_bone(A["rig"], "Head", f, rx=rx, rz=rz)
for f, ry in [(1, 0.0), (20, 0.0), (28, 1.1), (36, 0.8), (44, 1.1), (52, 0.0), (72, 0.0)]:
    key_bone(A["rig"], "ArmL", f, ry=ry)
key_bone(A["rig"], "ArmR", 1)
key_bone(A["rig"], "ArmR", 72)

key_bone(B["rig"], "JawB", 1)
key_bone(B["rig"], "JawB", 72)
for f, rx in [(1, 0), (29, 0.1), (44, 0.0), (72, 0)]:
    key_bone(B["rig"], "Head", f, rx=rx)
key_bone(B["rig"], "ArmL", 1)
key_bone(B["rig"], "ArmL", 72)
key_bone(B["rig"], "ArmR", 1)
key_bone(B["rig"], "ArmR", 72)

B_JAW = [(73, 0.0), (77, 0.6), (81, 0.1), (85, 0.4), (89, 0.05), (93, 0.55),
         (97, 0.15), (101, 0.5), (105, 0.0), (109, 0.45), (113, 0.1),
         (117, 0.5), (121, 0.1), (125, 0.35), (129, 0.05), (133, 0.3),
         (137, 0.1), (141, 0.2), (144, 0.0)]
for f, v in B_JAW:
    key_bone(B["rig"], "JawB", f, rx=v)
for f, rx, rz in [(73, 0, 0), (77, 0.14, -0.03), (88, -0.04, 0),
                  (101, 0.14, 0.03), (117, 0.14, -0.03), (133, -0.03, 0), (144, 0, 0)]:
    key_bone(B["rig"], "Head", f, rx=rx, rz=rz)
for f, ry in [(73, 0.0), (93, 0.0), (101, -1.2), (109, -0.9), (117, -1.2), (129, 0.0), (144, 0.0)]:
    key_bone(B["rig"], "ArmR", f, ry=ry)
key_bone(B["rig"], "ArmL", 73)
key_bone(B["rig"], "ArmL", 144)

key_bone(A["rig"], "JawB", 73)
key_bone(A["rig"], "JawB", 144)
for f, rx in [(73, 0), (101, 0.12), (117, 0.12), (144, 0)]:
    key_bone(A["rig"], "Head", f, rx=rx)
key_bone(A["rig"], "ArmL", 73)
key_bone(A["rig"], "ArmL", 144)
t_anim = time.time() - t0

# ---- 6. save + render --------------------------------------------------------
t0 = time.time()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "R3blendapi.blend"))
S.render.image_settings.file_format = 'PNG'
if ONLY_F36:
    stills = (("R3blendapi_f36", 36),)
else:
    stills = (("R3blendapi_f01", 1), ("R3blendapi_f36", 36), ("R3blendapi_f108", 108))
for name, fr in stills:
    S.frame_set(fr)
    S.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
if not STILLS_ONLY and not ONLY_F36:
    S.render.image_settings.file_format = 'FFMPEG'
    S.render.ffmpeg.format = 'MPEG4'
    S.render.ffmpeg.codec = 'H264'
    S.render.filepath = os.path.join(OUT, "R3blendapi.mp4")
    bpy.ops.render.render(animation=True)
t_render = time.time() - t0

print("\nR3-BLENDAPI TIMINGS  model=%.1fs rig=%.1fs anim=%.1fs render=%.1fs total=%.1fs"
      % (t_model, t_rig, t_anim, t_render, time.time() - t_all))
print("R3-BLENDAPI DONE:", OUT)
