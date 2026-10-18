"""Refine eye surfaces, nails, teeth and bust clearance in a new source copy."""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
out = root / '.runtime/character-workshop'
destination = out / 'Moneypenny-Performance-Details.blend'
if destination.exists():
    raise SystemExit('Existing detailed scene preserved.')
bpy.ops.wm.open_mainfile(filepath=str(out / 'Moneypenny-Performance-Fitted.blend'))
body = bpy.data.objects['Adult_Anatomy_Surface']
rig = bpy.data.objects['Adult_Body_Rig']
tree = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
suit = bpy.data.objects['Office_Blouse_And_Skirt']
clearance_changes = 0
for vertex in suit.data.vertices:
    x, y, z = vertex.co
    if abs(x) < .20 and .99 < z < 1.30 and y < -.025:
        point, _, _, _ = tree.ray_cast(Vector((x, -.8, z)), Vector((0, 1, 0)))
        if point and y > point.y - .009:
            vertex.co.y = point.y - .009
            clearance_changes += 1
suit.data.update()
cornea = bpy.data.materials.new('Corneal optical surface')
cornea.use_nodes = True
shader = cornea.node_tree.nodes.get('Principled BSDF')
shader.inputs['Base Color'].default_value = (1, 1, 1, 1)
shader.inputs['Transmission Weight'].default_value = 1
shader.inputs['Roughness'].default_value = .025
shader.inputs['IOR'].default_value = 1.38
corneal_names = []
for side in ('Left', 'Right'):
    center = rig.data.bones[side + 'Eye'].head_local
    vertices, faces = [], []
    rings, sides = 8, 40
    for ring in range(rings + 1):
        radius = .006 * ring / rings
        depth = math.sqrt(.012 ** 2 - radius ** 2) + .00015
        for n in range(sides):
            angle = n * math.tau / sides
            vertices.append(center + Vector((radius * math.cos(angle), -depth, radius * math.sin(angle))))
            if ring:
                previous = (ring - 1) * sides
                current = ring * sides
                faces.append((previous + n, previous + (n + 1) % sides, current + (n + 1) % sides, current + n))
    mesh = bpy.data.meshes.new(side + ' corneal cap')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(side + '_Corneal_Surface', mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(cornea)
    obj.parent = rig
    group = obj.vertex_groups.new(name=side + 'Eye')
    group.add(list(range(len(vertices))), 1, 'REPLACE')
    modifier = obj.modifiers.new('Eye gaze', 'ARMATURE')
    modifier.object = rig
    for face in mesh.polygons:
        face.use_smooth = True
    corneal_names.append(obj.name)
for obj in bpy.data.objects:
    if obj.parent != rig or obj.type != 'MESH':
        continue
    if 'nails' in obj.name:
        for mat in obj.data.materials:
            if mat and mat.use_nodes:
                shader = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if shader:
                    shader.inputs['Roughness'].default_value = .24
                    shader.inputs['Coat Weight'].default_value = .3
                    shader.inputs['Coat Roughness'].default_value = .18
    if 'teeth_base' in obj.name:
        for mat in obj.data.materials:
            if mat and mat.use_nodes:
                shader = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if shader:
                    shader.inputs['Roughness'].default_value = .28
                    shader.inputs['Subsurface Weight'].default_value = .035
body['detail_scope'] = 'Textured skin, pores, nipple/navel targets, external anatomical surface, perianal contour, body hair, separate fitted nails, facial morphs, teeth/tongue and gaze-linked corneal caps. Source modelling, not scan/medical certification.'
report = {'corneal_surfaces': corneal_names, 'additional_bust_clearance_vertices': clearance_changes,
          'bust_clearance_m': .009, 'nails': 'Separate fitted finger/toenail meshes, gloss/coat material',
          'teeth': 'Fitted enamel surface, transferred speech deformations',
          'photographic_realism_verified': False, 'extreme_pose_fit_verified': False}
(out / 'performance-detail-report.json').write_text(json.dumps(report, indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
print('PERFORMANCE_DETAILS_SAVED', json.dumps(report), flush=True)
