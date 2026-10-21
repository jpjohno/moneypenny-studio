"""One private, clothed v39 look-development candidate from the saved v38 GLB.

Reduce crown loft, replace sparse brow filaments with a surface-following
short groom, relax shallow blouse dents, and retain the original rig and every
body/face shape coordinate. No downloads, source overwrite, anatomy work or runtime promotion.
Run: Blender -b -t 2 --python scripts/character/refine_look_v39.py -- REPO
"""
from array import array
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

root = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
work = root / '.runtime/character-workshop'
review = root / '.runtime/v39-review'
review.mkdir(parents=True, exist_ok=True)
source = work / 'Moneypenny-Style-v38.glb'
candidate = work / 'Moneypenny-Style-v39.glb'
blend = work / 'Moneypenny-Style-v39.blend'
if candidate.exists() or blend.exists():
    raise SystemExit('Existing v39 candidate preserved; review it before proceeding')
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = bpy.data.objects['Adult_Anatomy_Surface']
hair = bpy.data.objects['Soft_Wavy_Bob']
garment = bpy.data.objects['Office_Blouse_And_Skirt']
brows = bpy.data.objects['Brow_Individual_Strands']
old_brow_names = [key.name for key in brows.data.shape_keys.key_blocks]


def keys(obj):
    return list(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else []


def relative_digest(obj):
    """Float-tolerant verification is separate; this records original deltas."""
    basis = keys(obj)[0]
    return {key.name: [key.data[i].co - basis.data[i].co
                       for i in range(len(basis.data))] for key in keys(obj)[1:]}


def geometry_digest(obj):
    digest = hashlib.sha256()
    data = keys(obj)[0].data if keys(obj) else obj.data.vertices
    values = array('f', [0.0]) * (len(data) * 3)
    data.foreach_get('co', values)
    digest.update(values.tobytes())
    for key in keys(obj)[1:]:
        key.data.foreach_get('co', values)
        digest.update(values.tobytes())
    return digest.hexdigest()


original_meshes = [o for o in bpy.data.objects if o.type == 'MESH']
original_hashes = {o.name: geometry_digest(o) for o in original_meshes}
def garment_contract(obj):
    return (
        tuple(tuple(p.vertices) for p in obj.data.polygons),
        tuple(p.material_index for p in obj.data.polygons),
        tuple((layer.name, tuple(tuple(v.uv) for v in layer.data)) for layer in obj.data.uv_layers),
        tuple(tuple((obj.vertex_groups[g.group].name, g.weight) for g in v.groups) for v in obj.data.vertices),
        repr(sorted(obj.items())),
    )
original_garment_contract = garment_contract(garment)
original_rig = [(b.name, b.parent.name if b.parent else None,
                 list(b.matrix_local)) for b in rig.data.bones]
body_before = [v.co.copy() for v in keys(body)[0].data]
relative_before = relative_digest(body)
# Warmth belongs to the removable runtime expression. Keep the exact original
# facial Basis and every viseme, including PP lip closure, unchanged.
face_max = 0.0
face_changed = 0

base = keys(body)[0]
face_tree = BVHTree.FromPolygons([v.co for v in base.data],
                               [list(p.vertices) for p in body.data.polygons])
nearest = KDTree(len(base.data))
for index, point in enumerate(base.data):
    nearest.insert(point.co, index)
nearest.balance()
# Short overlapping tapered brow ribbons, rooted on the actual face, with a
# restrained arch and warmer dark-blonde shade. Preserve all brow target names.
rng = random.Random(2026102139)
vertices, faces = [], []
for side in (-1, 1):
    for _ in range(620):
        t = rng.random()
        taper = max(.12, math.sin(math.pi * (t * .86 + .08)))
        x = side * (.013 + .043 * t)
        z = 1.497 + .006 * math.sin(t * math.pi) - .0045 * t
        z += rng.uniform(-.00125, .00125) * taper
        length = rng.uniform(.0016, .0030) * (.75 + .25 * taper)
        start = len(vertices)
        for step in range(4):
            u = step / 3
            px = x + side * length * u * (.45 + .5 * t)
            pz = z + length * u * (.80 - .70 * t)
            hit, normal, _, _ = face_tree.ray_cast(Vector((px, -.35, pz)),
                                                  Vector((0, 1, 0)))
            if hit is None:
                raise RuntimeError('Brow groom missed the face surface')
            centre = hit + normal * .00018
            radius = .000065 * (1 - .94 * u)
            vertices.extend((centre + Vector((radius, 0, 0)),
                             centre - Vector((radius, 0, 0))))
            if step:
                faces.append((start + (step - 1) * 2, start + step * 2,
                              start + step * 2 + 1, start + (step - 1) * 2 + 1))
new_mesh = bpy.data.meshes.new('v39 surface-following tapered brow groom')
new_mesh.from_pydata(vertices, [], faces)
new_mesh.update()
old_mesh = brows.data
new_mesh.materials.append(old_mesh.materials[0])
brows.shape_key_clear()
brows.data = new_mesh
brows.vertex_groups.clear()
head_name = next(b.name for b in rig.data.bones if b.name.split(':')[-1] == 'Head')
brows.vertex_groups.new(name=head_name).add(list(range(len(vertices))), 1, 'REPLACE')
brows.shape_key_add(name='Basis')
mapping = [nearest.find(v.co)[1] for v in new_mesh.vertices]
for name in old_brow_names[1:]:
    target = brows.shape_key_add(name=name)
    original = body.data.shape_keys.key_blocks.get(name)
    if original:
        for index, near in enumerate(mapping):
            target.data[index].co += original.data[near].co - base.data[near].co
brow_shader = next(n for n in new_mesh.materials[0].node_tree.nodes
                   if n.type == 'BSDF_PRINCIPLED')
brow_shader.inputs['Base Color'].default_value = (.055, .031, .014, 1)
brow_shader.inputs['Roughness'].default_value = .78
brow_shader.inputs['Specular IOR Level'].default_value = .12
brows['groom_revision'] = 'v39 — 1240 short surface-following brow hairs, all existing expression names'


def smooth(a, b, value):
    t = max(0, min(1, (value - a) / (b - a)))
    return t * t * (3 - 2 * t)


# Keep the existing authored bob and UV atlas. Lower its excessive crown loft
# while retaining the approved v38 eye-clear fringe without a new flat edge.
hair_changed, hair_max = 0, 0.0
for vertex in hair.data.vertices:
    p = vertex.co
    delta = Vector()
    delta.z -= .010 * smooth(1.53, 1.63, p.z)
    p += delta
    if delta.length > 1e-8:
        hair_changed += 1
        hair_max = max(hair_max, delta.length)
hair.data.update()
# Base-color multiplication exports as an ordinary glTF factor; keep the atlas,
# transparency, local normal map and lightweight card topology.
hair_mat = hair.data.materials[0]
shader = next(n for n in hair_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
source_link = shader.inputs['Base Color'].links[0]
source_socket = source_link.from_socket
hair_mat.node_tree.links.remove(source_link)
multiply = hair_mat.node_tree.nodes.new('ShaderNodeMix')
multiply.data_type = 'RGBA'
multiply.name = 'v39 neutral beige blonde tint'
multiply.blend_type = 'MULTIPLY'
multiply.inputs[0].default_value = 1
color_a = next(s for s in multiply.inputs if s.name == 'A' and s.type == 'RGBA')
color_b = next(s for s in multiply.inputs if s.name == 'B' and s.type == 'RGBA')
color_b.default_value = (.78, .88, .72, 1)
hair_mat.node_tree.links.new(source_socket, color_a)
hair_mat.node_tree.links.new(next(s for s in multiply.outputs if s.type == 'RGBA'), shader.inputs['Base Color'])
shader.inputs['Roughness'].default_value = .62
shader.inputs['Specular IOR Level'].default_value = .18
hair['groom_revision'] = 'v39 — conservative crown refit; approved v38 front fringe unchanged; existing atlas retained'

# Relax only small dents in the clothed blouse. Weld adjacency virtually so UV
# split vertices receive the same movement, retaining UVs, skin weights and all
# seam/material topology. Pin neckline, placket, cuffs, hem and skirt.
clusters = {}
for v in garment.data.vertices:
    clusters.setdefault(tuple(round(c, 6) for c in v.co), []).append(v.index)
cluster_list = list(clusters.values())
cluster_for = {i: group for group, ids in enumerate(cluster_list) for i in ids}
positions = [garment.data.vertices[ids[0]].co.copy() for ids in cluster_list]
original = [p.copy() for p in positions]
adjacent = [set() for _ in positions]
for edge in garment.data.edges:
    a, b = (cluster_for[i] for i in edge.vertices)
    if a != b:
        adjacent[a].add(b)
        adjacent[b].add(a)
weights = []
for p in positions:
    w = smooth(1.015, 1.055, p.z) * (1 - smooth(1.31, 1.355, p.z))
    w *= 1 - smooth(.34, .40, abs(p.x))
    # Preserve the front placket and collar opening exactly.
    if p.y < -.025:
        w *= smooth(.012, .030, abs(p.x))
    weights.append(w)
for _ in range(32):
    updated = []
    for index, p in enumerate(positions):
        ids = adjacent[index]
        if not ids or weights[index] == 0:
            updated.append(p)
            continue
        centre = sum((positions[j] for j in ids), Vector()) / len(ids)
        new = p.lerp(centre, .28 * weights[index])
        delta = new - original[index]
        if delta.length > .006:
            new = original[index] + delta.normalized() * .006
        updated.append(new)
    positions = updated
cloth_max, cloth_changed = 0.0, 0
for index, ids in enumerate(cluster_list):
    delta = positions[index] - original[index]
    if delta.length > 1e-7:
        cloth_changed += len(ids)
        cloth_max = max(cloth_max, delta.length)
    for vertex in ids:
        garment.data.vertices[vertex].co += delta
if garment.data.has_custom_normals:
    garment.data.normals_split_custom_set([(0, 0, 0)] * len(garment.data.loops))
for polygon in garment.data.polygons:
    polygon.use_smooth = True
garment.data.update()
for material in garment.data.materials:
    if 'blouse' not in material.name.lower():
        continue
    cloth_shader = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    cloth_shader.inputs['Roughness'].default_value = .80
    cloth_shader.inputs['Specular IOR Level'].default_value = .16
    cloth_shader.inputs['Sheen Weight'].default_value = .16
    material['fit_revision'] = 'v39 — shallow dent relaxation, seams and original skin weights retained'
for material in body.data.materials:
    skin_shader = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    skin_shader.inputs['Specular IOR Level'].default_value = .23
    for node in material.node_tree.nodes:
        if node.type == 'NORMAL_MAP':
            node.inputs['Strength'].default_value = .30

# Verify preserved data before exporting. Non-face body is byte-identical;
# all original facial targets remain unchanged, including the neutral rest.
non_face_unchanged = all((point.co - old).length == 0
                         for point, old in zip(base.data, body_before) if old.z <= 1.395)
assert non_face_unchanged
assert geometry_digest(body) == original_hashes[body.name]
assert garment_contract(garment) == original_garment_contract
maximum_delta_error = max((key.data[i].co - base.data[i].co - delta).length
                          for key in keys(body)[1:]
                          for i, delta in enumerate(relative_before[key.name]))
assert maximum_delta_error < 2e-7, maximum_delta_error
preserved_meshes = [o.name for o in original_meshes
                    if o not in (body, hair, garment, brows)
                    and geometry_digest(o) == original_hashes[o.name]]
# Verify important hands/feet/teeth/eye geometry individually.
for o in original_meshes:
    if 'nails' in o.name or 'Corneal' in o.name or 'high-poly' in o.name:
        assert geometry_digest(o) == original_hashes[o.name], o.name
assert original_rig == [(b.name, b.parent.name if b.parent else None,
                         list(b.matrix_local)) for b in rig.data.bones]
assert [key.name for key in keys(brows)] == old_brow_names
rig['surface_revision'] = 'v39 candidate — clothed portrait grooming and shallow fabric relaxation'
bpy.ops.export_scene.gltf(filepath=str(candidate), export_format='GLB',
                          export_animations=False, export_morph=True,
                          export_skins=True, export_extras=True, export_apply=False)
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
# The exporter should represent the color multiplier without baking a new map.
import struct
raw = candidate.read_bytes()
size = struct.unpack_from('<I', raw, 12)[0]
json_part = json.loads(raw[20:20 + size])
export_hair = next(m for m in json_part['materials'] if m['name'] == 'VitHair')
tint_exported = export_hair['pbrMetallicRoughness'].get('baseColorFactor')
assert tint_exported and max(abs(a-b) for a,b in zip(tint_exported, (.78,.88,.72,1))) < .001, tint_exported
report = {
    'revision': 'v39-candidate', 'source': str(source), 'source_sha256': source_hash,
    'candidate': str(candidate), 'bytes': candidate.stat().st_size,
    'body_below_face_unchanged': non_face_unchanged,
    'entire_body_face_basis_and_all_shape_coordinates_byte_identical': True,
    'mouth_warmth': 'removable runtime expression; original authored lip seal retained',
    'visual_correction': 'Removed flattened central fringe sweep after first render',
    'face_rest_vertices_adjusted': face_changed, 'maximum_face_rest_offset_m': face_max,
    'maximum_relative_body_morph_delta_error_m': maximum_delta_error,
    'body_morph_names_retained': len(keys(body))-1, 'brow_morph_names_retained': len(keys(brows))-1,
    'bones_unchanged': len(rig.data.bones), 'unchanged_meshes': preserved_meshes,
    'brow_hairs': 1240, 'hair_vertices_refitted': hair_changed,
    'maximum_hair_refit_m': hair_max, 'hair_base_color_factor': tint_exported,
    'cloth_vertices_relaxed': cloth_changed, 'maximum_cloth_relaxation_m': cloth_max,
    'garment_vertex_count_retained': len(garment.data.vertices),
    'garment_weights_uvs_topology_and_fallback_metadata_retained': True,
    'new_downloads': 0, 'photographic_realism_verified': False,
    'native_render_review_required': True, 'browser_acceptance': False, 'promoted': False,
    'limits': ['Existing coarse card groom and baked hair highlights remain',
               'Existing skin color atlas and head topology remain',
               'No captured skin, groom simulation or cloth simulation added']
}
(work / 'style-v39-report.json').write_text(json.dumps(report, indent=2) + '\n')
# Copy exactly the baseline camera, lighting, world and color management.
with bpy.data.libraries.load(str(review / 'v38-review.blend'), link=False) as (available, loaded):
    loaded.objects = [name for name in available.objects if name in ('Camera', 'Key', 'Fill', 'Rim')]
    loaded.worlds = ['Fixed neutral review']
for obj in loaded.objects:
    bpy.context.scene.collection.objects.link(obj)
scene = bpy.context.scene
scene.world = loaded.worlds[0]
scene.camera = next(o for o in loaded.objects if o.type == 'CAMERA')
scene.render.engine = 'CYCLES'; scene.cycles.samples = 24; scene.cycles.use_denoising = True
scene.render.threads_mode = 'FIXED'; scene.render.threads = 2
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'; scene.view_settings.exposure = 0
camera = scene.camera

def shot(name, target, scale, resolution, angle=0):
    camera.location = (math.sin(angle) * 2.1, -math.cos(angle) * 2.1, target)
    camera.rotation_euler = (Vector((0, 0, target))-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = scale
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(review / name)
    bpy.ops.render.render(write_still=True)

shot('v39-portrait.png', 1.47, .52, (480, 600))
shot('v39-full.png', .87, 1.9, (384, 640))
shot('v39-quarter.png', 1.47, .52, (480, 600), .55)
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
print('V39_CANDIDATE', json.dumps(report), flush=True)
