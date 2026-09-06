# Track C helper — generate ONE finalized MB-Lab character.
# Usage: blender -b -P trackC_mblab/gen_char.py -- <template> <out.blend>
# Example: blender -b -P trackC_mblab/gen_char.py -- human_female_base charA.blend

import bpy, sys, time

t0 = time.time()
argv = sys.argv[sys.argv.index("--") + 1:]
template, out = argv[0], argv[1]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.preferences.addon_enable(module='mblab')

from mblab import mblab_humanoid as _h  # noqa: F401  (ensures session module loaded)
scn = bpy.context.scene
print("available templates:", sorted(__import__('mblab', fromlist=['mblab_humanoid']).mblab_humanoid.characters_config.keys()))
scn.mblab_template_name = template
bpy.ops.mbast.init_character()
try:
    scn.mbcrea_texture_melanin = 0.12  # lighter phenotype for readability
    bpy.context.view_layer.update()
except Exception as e:
    print('melanin tweak skipped:', e)
bpy.ops.mbast.finalize_character()

meshes = [o for o in bpy.data.objects if o.type == 'MESH' and len(o.data.polygons) > 1000]
rigs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
print("GEN %s: mesh=%s polys=%d rig=%s bones=%d" % (
    template, meshes[0].name, len(meshes[0].data.polygons),
    rigs[0].name, len(rigs[0].data.bones)))
bpy.ops.wm.save_as_mainfile(filepath=out)
print("GEN DONE in %.1fs -> %s" % (time.time() - t0, out))
