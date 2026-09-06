# Export track characters to GLB for the web viewer (Track F).
# Usage: BLEND_IN=../output/trackA.blend GLB_OUT=../viewer/trackA.glb \
#        blender -b -P trackF_web/export_glb.py

import bpy, os

blend = os.environ["BLEND_IN"]
out = os.environ["GLB_OUT"]
bpy.ops.wm.open_mainfile(filepath=blend)
S = bpy.context.scene
S.frame_start, S.frame_end = 1, 144
# keep only character content (drop camera/lights/ground stain)
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT') or o.name.lower().startswith(('ground', 'plane')):
        bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.export_scene.gltf(
    filepath=out, export_format='GLB',
    export_animations=True, export_frame_range=True,
    export_force_sampling=True, export_nla_strips=False,
    export_def_bones=False)
print("GLB DONE:", out, os.path.getsize(out), "bytes")
