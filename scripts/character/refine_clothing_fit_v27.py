"""Refit only the v26 blouse's inflated front shell; preserve the body and rig."""
import hashlib
import json
import sys
from array import array
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
out = root / '.runtime/character-workshop'
source = out / 'Moneypenny-Style-v26.blend'
dest = out / 'Moneypenny-Style-v27.blend'
glb = out / 'Moneypenny-Style-v27.glb'
if dest.exists() or glb.exists():
    raise SystemExit('Existing v27 preserved')
bpy.ops.wm.open_mainfile(filepath=str(source))
rig = bpy.data.objects['Adult_Body_Rig']
body = bpy.data.objects['Adult_Anatomy_Surface']
garment = bpy.data.objects['Office_Blouse_And_Skirt']
parts = [o for o in bpy.data.objects if o.parent == rig and o.type == 'MESH' and not o.hide_render]

def surface_digest():
    digest = hashlib.sha256()
    for key in body.data.shape_keys.key_blocks:
        digest.update(key.name.encode())
        coordinates = array('f', [0.]) * (len(key.data)*3)
        key.data.foreach_get('co', coordinates)
        digest.update(coordinates.tobytes())
    return digest.hexdigest()

body_before = surface_digest()
# Shape-key Basis coordinates differ from mesh.vertices after the earlier style
# edits. Evaluate those keys and surface smoothing in rest space for fitting.
armature_modifiers = [modifier for modifier in body.modifiers if modifier.type == 'ARMATURE']
modifier_states = [modifier.show_viewport for modifier in armature_modifiers]
for modifier in armature_modifiers:
    modifier.show_viewport = False
depsgraph = bpy.context.evaluated_depsgraph_get()
depsgraph.update()
evaluated = body.evaluated_get(depsgraph)
surface_mesh = evaluated.to_mesh()
tree = BVHTree.FromPolygons([v.co.copy() for v in surface_mesh.vertices], [list(p.vertices) for p in surface_mesh.polygons])
evaluated.to_mesh_clear()
for modifier, enabled in zip(armature_modifiers, modifier_states):
    modifier.show_viewport = enabled
depsgraph.update()

def front_surface(x, z):
    point, _, _, _ = tree.ray_cast(Vector((x, -.6, z)), Vector((0, 1, 0)), 1.)
    return point.y if point is not None else None

def smoothstep(low, high, value):
    value = min(1., max(0., (value-low)/(high-low)))
    return value*value*(3.-2.*value)

garment_tree = BVHTree.FromPolygons([v.co.copy() for v in garment.data.vertices], [list(p.vertices) for p in garment.data.polygons])
def garment_front(x, z):
    point, _, _, _ = garment_tree.ray_cast(Vector((x, -.6, z)), Vector((0, 1, 0)), 1.)
    return point.y if point is not None else None

def hanging_front(x, z):
    bottom, top = garment_front(x, 1.017), garment_front(x, 1.16)
    if bottom is None or top is None:
        return None
    def line(height):
        return bottom+(top-bottom)*(height-1.017)/.143
    # Move a whole vertical fabric span as one continuous piece, rather than
    # independently projecting vertices (which creates many small ripples).
    penetration = 0.
    for height in [1.025+i*.005 for i in range(28)]:
        surface = front_surface(x, height)
        if surface is not None:
            penetration = max(penetration, line(height)-(surface-.009))
    return line(z)-penetration

original_y = [vertex.co.y for vertex in garment.data.vertices]
weights = []
for vertex in garment.data.vertices:
    p = vertex.co
    weight = 0.
    if 1.014 < p.z < 1.185 and .02 < abs(p.x) < .235 and p.y < -.075:
        weight = (smoothstep(1.014, 1.03, p.z)*(1-smoothstep(1.15, 1.185, p.z))
                  *smoothstep(.02, .04, abs(p.x))*(1-smoothstep(.175, .235, abs(p.x))))
    weights.append(weight)

changed = 0
movements = []
gaps_before = []
gaps_after = []
for vertex in garment.data.vertices:
    p = vertex.co
    if not weights[vertex.index]:
        continue
    surface = front_surface(p.x, p.z)
    if surface is None:
        continue
    desired = hanging_front(p.x, p.z)
    if desired is None:
        continue
    movement = (desired-p.y)*weights[vertex.index]
    if abs(movement) < 1e-6:
        continue
    gaps_before.append(surface-p.y)
    p.y += movement
    gaps_after.append(surface-p.y)
    movements.append(movement)
    changed += 1
garment.data.update()
assert surface_digest() == body_before, 'Body or facial shape coordinates changed'
rig['surface_revision'] = 'v27 — garment-only front drape repair; v26 body, face, hair and rig preserved'

for obj in bpy.context.selected_objects:
    obj.select_set(False)
rig.select_set(True)
for obj in parts:
    obj.hide_set(False)
    obj.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.wm.save_as_mainfile(filepath=str(dest))

# Preserve the existing clothed browser coverage mask, without editing the saved
# authoring surface or changing any anatomy coordinates.
for obj in bpy.context.selected_objects:
    obj.select_set(False)
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')
bpy.ops.object.mode_set(mode='OBJECT')
masked = 0
for face in body.data.polygons:
    if .99 < face.center.z < 1.285 and abs(face.center.x) < .20:
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
assert glb.stat().st_size < 80*1024*1024
report = {
    'revision': 'v27', 'source': source.name, 'bytes': glb.stat().st_size,
    'garment_vertices_refitted': changed, 'maximum_inward_refit_m': max(movements, default=0),
    'maximum_outward_drape_m': -min(movements, default=0),
    'mean_front_gap_before_m': sum(gaps_before)/max(1,len(gaps_before)),
    'mean_front_gap_after_m': sum(gaps_after)/max(1,len(gaps_after)),
    'body_and_all_facial_shape_coordinates_preserved': True,
    'body_surface_sha256': body_before, 'covered_export_faces': masked,
    'photographic_realism_verified': False,
}
(out/'style-v27-report.json').write_text(json.dumps(report, indent=2))
print('FIT_COMPLETE', json.dumps(report), flush=True)
