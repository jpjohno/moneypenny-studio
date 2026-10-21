"""Read-only structural and neutral studio-render inspection of the body study."""
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

root = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
out = root / '.runtime/character-workshop'
bpy.ops.wm.open_mainfile(filepath=str(out / 'Moneypenny-Adult-Anatomy-Study-v3.blend'))
body = bpy.data.objects['Adult_Anatomy_Surface']
rig = bpy.data.objects['Adult_Body_Rig']
bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
patch_boundary_edges = [e for e in bm.edges if abs(e.verts[0].co.x) < .05 and e.verts[0].co.z < .80
                        and e.verts[0].co.z > .72 and len(e.link_faces) != 2]
invalid = sum(not math.isfinite(c) for v in body.data.vertices for c in v.co)
unweighted = sum(not any(body.vertex_groups[g.group].name in rig.data.bones and g.weight > 0 for g in v.groups)
                 for v in body.data.vertices)
baseline = [v.co.copy() for v in body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
shape_checks = {}
shape_movements = {}
for key in body.data.shape_keys.key_blocks[1:]:
    previous = key.value
    samples = []
    movement = 0
    for value in (key.slider_min, key.slider_max):
        key.value = value
        bpy.context.view_layer.update()
        current = [v.co.copy() for v in body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
        samples.append(all(math.isfinite(c) for v in current for c in v))
        movement = max(movement, max((a - b).length for a, b in zip(baseline, current)))
    key.value = previous
    shape_checks[key.name] = all(samples)
    shape_movements[key.name] = movement
bpy.context.view_layer.update()
# A moderate asymmetric arm/hip check catches detached weights and NaNs.
rig.pose.bones['mixamorig:LeftArm'].rotation_mode = 'XYZ'
rig.pose.bones['mixamorig:LeftArm'].rotation_euler.y = .45
rig.pose.bones['mixamorig:LeftUpLeg'].rotation_mode = 'XYZ'
rig.pose.bones['mixamorig:LeftUpLeg'].rotation_euler.x = -.45
bpy.context.view_layer.update()
posed = [v.co.copy() for v in body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
maximum_movement = max((a - b).length for a, b in zip(baseline, posed))
pose_finite = all(math.isfinite(c) for v in posed for c in v)
for bone in rig.pose.bones:
    bone.rotation_euler = (0, 0, 0)
bpy.context.view_layer.update()
report = {'finite_mesh': invalid == 0, 'unweighted_body_vertices': unweighted,
          'anatomical_patch_nonmanifold_edges': len(patch_boundary_edges),
          'body_total_nonmanifold_edges': sum(not e.is_manifold for e in bm.edges),
          'moderate_pose_finite': pose_finite, 'moderate_pose_max_displacement_m': maximum_movement,
          'shape_control_extremes_finite': shape_checks,
          'shape_control_max_displacement_m': shape_movements,
          'visual_review_pending': True, 'extreme_pose_acceptance': False}
bm.free()
if (invalid or unweighted or report['body_total_nonmanifold_edges'] or not pose_finite
        or maximum_movement < .01 or not all(shape_checks.values()) or min(shape_movements.values()) < 1e-6):
    raise ValueError('Body structural/rig inspection failed: ' + json.dumps(report))
(out / 'anatomy-inspection.json').write_text(json.dumps(report, indent=2))
print('ANATOMY_INSPECTION', json.dumps(report), flush=True)
scene = bpy.context.scene
data = bpy.data.cameras.new('Neutral anatomy review')
camera = bpy.data.objects.new('Neutral anatomy review', data)
scene.collection.objects.link(camera)
data.type = 'ORTHO'
data.ortho_scale = 1.9
scene.camera = camera
scene.render.resolution_x = 700
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.eevee.taa_render_samples = 24
for label, pos in [('front', (0, -3, .88)), ('rear', (0, 3, .88)), ('side', (3, 0, .88))]:
    camera.location = pos
    camera.rotation_euler = (Vector((0, 0, .80)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(root / 'verification' / ('anatomy-' + label + '.png'))
    bpy.ops.render.render(write_still=True)
