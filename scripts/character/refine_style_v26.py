"""Reduce the v25 profile volume and refit the clothed performance candidate."""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
out = root / '.runtime/character-workshop'
source = out / 'Moneypenny-Style-v25.blend'
dest = out / 'Moneypenny-Style-v26.blend'
glb = out / 'Moneypenny-Style-v26.glb'
if dest.exists() or glb.exists():
    raise SystemExit('Existing v26 preserved')

bpy.ops.wm.open_mainfile(filepath=str(source))
rig = bpy.data.objects['Adult_Body_Rig']
body = bpy.data.objects['Adult_Anatomy_Surface']
garment = bpy.data.objects['Office_Blouse_And_Skirt']
parts = [obj for obj in bpy.data.objects if obj.parent == rig and obj.type == 'MESH' and not obj.hide_render]

def reduction(point):
    """Undo roughly half of v25's forward/pointed bust field with a broad taper."""
    centre = Vector((.10 if point.x >= 0 else -.10, -.23, 1.16))
    delta = point - centre
    weight = math.exp(-((delta.x / .125) ** 4 + (delta.z / .105) ** 4) * 1.22)
    front = max(0.0, min(1.0, (-point.y - .06) / .15))
    amount = weight * front
    result = point.copy()
    result.y += .075 * amount
    result.x -= (point.x - centre.x) * .13 * amount
    result.z -= (point.z - centre.z) * .08 * amount
    return result - point

changed = 0
for obj in (body, garment):
    basis = obj.data.shape_keys.key_blocks[0] if obj.data.shape_keys else None
    coordinates = [v.co.copy() for v in (basis.data if basis else obj.data.vertices)]
    for index, point in enumerate(coordinates):
        delta = reduction(point)
        if delta.length < 1e-7:
            continue
        if obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:
                key.data[index].co += delta
        else:
            obj.data.vertices[index].co += delta
        changed += 1
    obj.data.update()

# Re-establish a small, even cloth clearance after changing the shared silhouette.
tree = BVHTree.FromPolygons([v.co for v in body.data.vertices], [list(p.vertices) for p in body.data.polygons])
clearance = 0
for vertex in garment.data.vertices:
    point, normal, _, distance = tree.find_nearest(vertex.co)
    if point is not None and distance < .045 and (vertex.co - point).dot(normal) < .0045:
        vertex.co = point + normal * .005
        clearance += 1

rig['surface_revision'] = 'v26 — balanced bust profile, fitted blouse, v25 face hair voice and motion contract'
for obj in bpy.context.selected_objects:
    obj.select_set(False)
rig.select_set(True)
for obj in parts:
    obj.hide_set(False)
    obj.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.wm.save_as_mainfile(filepath=str(dest))

# Only the browser export receives the normal under-garment coverage mask.
for obj in bpy.context.selected_objects:
    obj.select_set(False)
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')
bpy.ops.object.mode_set(mode='OBJECT')
masked = 0
for face in body.data.polygons:
    point = face.center
    if .99 < point.z < 1.285 and abs(point.x) < .20:
        face.select = True
        masked += 1
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.delete(type='ONLY_FACE')
bpy.ops.object.mode_set(mode='OBJECT')
rig.select_set(True)
for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True,
                          export_animations=False, export_morph=True, export_skins=True,
                          export_extras=True, export_apply=False)
if glb.stat().st_size > 80 * 1024 * 1024:
    raise ValueError('Browser asset exceeds size budget')
report = {
    'revision': 'v26',
    'bytes': glb.stat().st_size,
    'profile_reduction_max_m': .075,
    'deformed_vertices': changed,
    'garment_clearance_corrections': clearance,
    'export_covered_faces': masked,
    'source_v25_preserved': True,
    'photographic_realism_verified': False,
}
(out / 'style-v26-report.json').write_text(json.dumps(report, indent=2))
print('STYLE_COMPLETE', json.dumps(report), flush=True)
