"""Fit actual garment vertices and add an original skinned strand groom."""
import json
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
out = root / '.runtime/character-workshop'
destination = out / 'Moneypenny-Performance-Fitted.blend'
if destination.exists():
    raise SystemExit('Existing fitted performance scene preserved.')
bpy.ops.wm.open_mainfile(filepath=str(out / 'Moneypenny-Performance-Character.blend'))
body = bpy.data.objects['Adult_Anatomy_Surface']
rig = bpy.data.objects['Adult_Body_Rig']
deps = bpy.context.evaluated_depsgraph_get()
tree = BVHTree.FromObject(body, deps)
fit = {}
for name in ['Office_Blouse_And_Skirt', 'Office_Ankle_Shoes']:
    obj = bpy.data.objects[name]
    for selected in bpy.context.selected_objects:
        selected.select_set(False)
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for modifier in list(obj.modifiers):
        if modifier.type == 'SUBSURF':
            modifier.levels = 2 if name.startswith('Office_Blouse') else 1
            bpy.ops.object.modifier_apply(modifier=modifier.name)
    corrected = 0
    for vertex in obj.data.vertices:
        point, normal, _, distance = tree.find_nearest(vertex.co)
        if point is None:
            continue
        signed = (vertex.co - point).dot(normal)
        if signed < .004 and distance < .10:
            vertex.co = point + normal * .004
            corrected += 1
    obj.data.update()
    fit[name] = {'vertices': len(obj.data.vertices), 'outside_fit_corrections': corrected, 'allowance_m': .004}
    obj['fit_scope'] = 'Rest-pose outside-surface fitting at 4mm; movement and body morph refitting still require inspection.'
# Preserve old authored hair as a base cap/ponytail. The strands are new original
# geometry; no claims that this procedural groom comes from a photographic scan.
for obj in bpy.data.objects:
    if obj.name.startswith('Adult_Body_Source.elvs_lara_hair'):
        obj.hide_render = True
        obj.hide_set(True)
    if obj.name.startswith('Adult_Body_Source.ponytail01'):
        obj.hide_render = False
        obj.hide_set(False)
source = bpy.data.objects['Adult_Body_Source']
sys.path.insert(0, str(Path(__file__).parent))
from refine_body import rest_coordinates
coords = rest_coordinates(source)
scalp = source.vertex_groups['scalp'].index
scalp_ids = {v.index for v in source.data.vertices if any(g.group == scalp and g.weight > .5 for g in v.groups)}
faces = [f for f in source.data.polygons if all(i in scalp_ids for i in f.vertices)]
if not faces:
    raise ValueError('No actual scalp topology for strand roots.')
center = Vector((0, -.005, 1.48))
radii = Vector((.078, .092, .119))
tie = Vector((0, .085, 1.54))
end_direction = Vector((0, .85, .53)).normalized()
vertices, polygons, shades = [], [], []
rng = random.Random(18102026)
strand_count = 6500
for strand in range(strand_count):
    face = rng.choice(faces)
    a, b = rng.random(), rng.random()
    if a + b > 1:
        a, b = 1 - a, 1 - b
    ids = list(face.vertices)[:3]
    root_point = sum((coords[i] * w for i, w in zip(ids, (a, b, 1 - a - b))), Vector())
    # Omit the lower facial/scalp boundary rather than growing strands on cheeks.
    if root_point.z < 1.49 or root_point.y < -.075:
        continue
    start_direction = Vector(((root_point.x - center.x) / radii.x,
                              (root_point.y - center.y) / radii.y,
                              (root_point.z - center.z) / radii.z)).normalized()
    points = []
    jitter = rng.uniform(.0005, .0020)
    for step in range(9):
        t = step / 8
        direction = start_direction.lerp(end_direction, t).normalized()
        cap_point = center + Vector((direction.x * radii.x, direction.y * radii.y, direction.z * radii.z))
        cap_point += direction * (.002 + jitter)
        points.append(cap_point.lerp(root_point, (1 - t) ** 5))
    last = points[-1]
    tail_length = rng.uniform(.14, .22)
    for step in range(1, 6):
        t = step / 5
        points.append(last + Vector((math.sin(t * 6 + strand) * .003 * t,
                                     .014 * t + math.sin(t * 5) * .006,
                                     -tail_length * t)))
    start = len(vertices)
    shade = rng.randrange(5)
    for step, point in enumerate(points):
        tangent = (points[min(step + 1, len(points) - 1)] - points[max(0, step - 1)]).normalized()
        u = tangent.cross(Vector((1, 0, 0))).normalized()
        if u.length < .5:
            u = tangent.cross(Vector((0, 1, 0))).normalized()
        v = tangent.cross(u).normalized()
        t = step / (len(points) - 1)
        radius = rng.uniform(.000055, .000085) * (1 - .85 * t)
        for side in range(3):
            angle = side * math.tau / 3
            vertices.append(point + (u * math.cos(angle) + v * math.sin(angle)) * radius)
        if step:
            for side in range(3):
                polygons.append((start + (step - 1) * 3 + side, start + (step - 1) * 3 + (side + 1) % 3,
                                 start + step * 3 + (side + 1) % 3, start + step * 3 + side))
                shades.append(shade)
mesh = bpy.data.meshes.new('Original individually modelled hair strands')
mesh.from_pydata(vertices, [], polygons)
mesh.update()
groom = bpy.data.objects.new('Hair_Individual_Strands', mesh)
bpy.context.scene.collection.objects.link(groom)
groom.parent = rig
group = groom.vertex_groups.new(name='mixamorig:Head')
group.add(list(range(len(vertices))), 1, 'REPLACE')
modifier = groom.modifiers.new('Head skinning', 'ARMATURE')
modifier.object = rig
for n, color in enumerate([(.07, .025, .010, 1), (.11, .042, .016, 1), (.045, .014, .006, 1), (.15, .065, .025, 1), (.08, .03, .012, 1)]):
    material = bpy.data.materials.new('Natural strand tone ' + str(n))
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Roughness'].default_value = .36
    anisotropy = shader.inputs.get('Anisotropic')
    if anisotropy:
        anisotropy.default_value = .65
    mesh.materials.append(material)
for face, shade in zip(mesh.polygons, shades):
    face.material_index = shade
    face.use_smooth = True
groom['asset_source'] = 'Original procedural strand groom authored for this local source; not a photographic hair scan.'
groom['strand_count'] = len(vertices) // 42
report = {'fit': fit, 'original_hair_strands': groom['strand_count'], 'groom_vertices': len(vertices),
          'scope': 'Rest fitting and geometric strand groom; photographic quality and extreme-pose clothing fit need visual review.'}
(out / 'performance-fit-report.json').write_text(json.dumps(report, indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
print('PERFORMANCE_FIT_SAVED', json.dumps(report), flush=True)
