# Track E helper — generate ONE MPFB2 character headless (one session per char).
# Usage: blender -b -P trackE_mpfb/gen_char.py -- <gender01> <out.blend>
#   gender01: 1.0 = female (char A), 0.0 = male (char B)
# Needs: MPFB 2.0.17 installed as legacy addon (see notes in trackE metrics).
# Output: one .blend with rigged + weight-painted human (default rig, 163 bones).

import bpy, os, sys, time

t0 = time.time()
argv = sys.argv[sys.argv.index("--") + 1:]
gender, out = float(argv[0]), argv[1]

# Blender 4.0 compat: extension_path_user only exists in 4.2+
if not hasattr(bpy.utils, 'extension_path_user'):
    def _epu(package, **kw):
        p = os.path.expanduser(os.path.join("~", ".mpfb_user"))
        os.makedirs(p, exist_ok=True)
        return p
    bpy.utils.extension_path_user = _epu

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.preferences.addon_enable(module='mpfb')

import importlib
def dynamic_import(absolute_package_str, key):
    for amod in sys.modules:
        if amod.endswith(absolute_package_str):
            return getattr(importlib.import_module(amod), key)
    raise ValueError("No module " + absolute_package_str)

HumanService = dynamic_import("mpfb.services.humanservice", "HumanService")
HumanObjectProperties = dynamic_import("mpfb.entities.objectproperties", "HumanObjectProperties")
TargetService = dynamic_import("mpfb.services.targetservice", "TargetService")

t_model = time.time()
human = HumanService.create_human()
HumanObjectProperties.set_value("gender", gender, entity_reference=human)
TargetService.reapply_macro_details(human)
t_model = time.time() - t_model

t_rig = time.time()
rig = HumanService.add_builtin_rig(human, "default")
t_rig = time.time() - t_rig

print("GEN gender=%.1f: mesh=%s verts=%d vgroups=%d rig=%s bones=%d jaw=%s" % (
    gender, human.name, len(human.data.vertices), len(human.vertex_groups),
    rig.name, len(rig.data.bones), "jaw" in rig.data.bones))
bpy.ops.wm.save_as_mainfile(filepath=out)
print("GEN DONE model=%.1fs rig=%.1fs total=%.1fs -> %s"
      % (t_model, t_rig, time.time() - t0, out))
