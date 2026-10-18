"""Preserve the detailed scene and repair closed-shoe toe clearance."""
import json
from pathlib import Path
import sys

import bpy

root = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
out = root / '.runtime/character-workshop'
destination = out / 'Moneypenny-Performance-Final-Fit-v3.blend'
if destination.exists():
    raise SystemExit('Existing final-fit scene preserved.')
bpy.ops.wm.open_mainfile(filepath=str(out / 'Moneypenny-Performance-Details.blend'))
rig = bpy.data.objects['Adult_Body_Rig']
old_shoes = bpy.data.objects['Office_Ankle_Shoes']
# Start with the undistorted, source-fitted shoe asset. Closest-body projection
# created toe impressions in the leather and is deliberately not reused here.
with bpy.data.libraries.load(str(out / 'Moneypenny-Performance-Character.blend'), link=False) as (available, loaded):
    loaded.objects = ['Office_Ankle_Shoes']
shoes = loaded.objects[0]
bpy.data.objects.remove(old_shoes, do_unlink=True)
shoes.name = 'Office_Ankle_Shoes'
bpy.context.scene.collection.objects.link(shoes)
shoes.parent = rig
for modifier in shoes.modifiers:
    if modifier.type == 'ARMATURE':
        modifier.object = rig
for obj in bpy.context.selected_objects:
    obj.select_set(False)
shoes.hide_set(False)
shoes.select_set(True)
bpy.context.view_layer.objects.active = shoes
# Preserve the actual last, UVs, sole and skin weights; add a modest fitting
# allowance about each foot rather than sculpting the shoe around each toe.
for modifier in list(shoes.modifiers):
    if modifier.type == 'SUBSURF':
        modifier.levels = 1
        bpy.ops.object.modifier_apply(modifier=modifier.name)
for vertex in shoes.data.vertices:
    x, y, z = vertex.co
    center_x = .173 if x > 0 else -.173
    vertex.co.x = center_x + (x - center_x) * 1.10
    vertex.co.y = -.08 + (y + .08) * 1.10
    vertex.co.z = .06 + (z - .06) * 1.08
shoes.data.update()
shoes['fit_scope'] = 'Original source shoe last, 10% XY and 8% Z fitting allowance about each foot. Extreme motion and cloth simulation are not certified.'
report = {'shoe_vertices': len(shoes.data.vertices), 'source_last_preserved': True,
          'fit_scale_xyz': [1.10, 1.10, 1.08], 'photographic_realism_verified': False,
          'extreme_pose_fit_verified': False, 'live_browser_acceptance': False}
(out / 'performance-final-fit-report.json').write_text(json.dumps(report, indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
print('PERFORMANCE_FINAL_FIT_SAVED', json.dumps(report), flush=True)
