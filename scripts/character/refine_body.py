"""Create a separate neutral adult anatomical study in Blender 4.5.

Reads the existing source and locally installed asset data. Never overwrites an
artist-edited scene. This is source authoring, not live avatar replacement.
The legacy anatomical patch retains its embedded licence in the saved scene;
commercial redistribution is deliberately not certified.
"""
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector


def rest_coordinates(obj):
    """Evaluate shape keys with modifiers disabled; keep original vertex IDs."""
    state = [(m, m.show_viewport) for m in obj.modifiers]
    for m, _ in state:
        m.show_viewport = False
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    coords = [v.co.copy() for v in evaluated.data.vertices]
    for m, value in state:
        m.show_viewport = value
    bpy.context.view_layer.update()
    return coords


def skinned(obj, rig):
    obj.parent = rig
    modifier = obj.modifiers.new('Body skeleton', 'ARMATURE')
    modifier.object = rig
    modifier.use_deform_preserve_volume = True
    for face in obj.data.polygons:
        face.use_smooth = True


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    root = Path(args[0]).resolve()
    out = root / '.runtime/character-workshop'
    destination = out / 'Moneypenny-Adult-Anatomy-Study-v3.blend'
    if destination.exists():
        raise SystemExit('Existing anatomical study preserved: ' + str(destination))
    bpy.ops.wm.open_mainfile(filepath=str(out / 'Moneypenny-Adult-Body-Source.blend'))
    source = bpy.data.objects['Adult_Body_Source']
    rig = bpy.data.objects['Adult_Body_Rig']
    tools = root / '.runtime/character-tools'
    assets = tools / 'assets'
    patch_path = tools / 'mhx2-source/import_runtime_mhx2/data/hm8/genitalia/vulva.mxa'
    manifest = json.loads(Path(__file__).with_name('body-assets.json').read_text())
    if hashlib.sha256(patch_path.read_bytes()).hexdigest() != manifest['anatomy_source']['sha256']:
        raise ValueError('Anatomy data differs from the pinned source; preserved for review.')
    patch = json.loads(patch_path.read_text())
    if len(source.data.vertices) != 19158 or patch['proxy']['base_mesh'] != 'hm08':
        raise ValueError('This authoring path requires the verified hm08 adult base.')
    # Original profile is fixed adult; reject a source with changed age settings.
    from bl_ext.user_default.mpfb.services.targetservice import TargetService
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    from bl_ext.user_default.mpfb.entities.objectproperties import HumanObjectProperties
    age = HumanObjectProperties.get_value('age', entity_reference=source)
    if age is None or float(age) < .4:
        raise ValueError('An adult source profile is required.')
    import bl_ext.user_default.mpfb as mpfb
    targets = Path(mpfb.__file__).parent / 'data/targets'
    details = {'breast/nipple-point-incr': .22, 'breast/nipple-size-incr': .08,
               'stomach/stomach-navel-in': .12}
    for target, weight in details.items():
        TargetService.load_target(source, str(targets / (target + '.target.gz')), weight=weight)
    coords = rest_coordinates(source)
    groups = {g.index: g.name for g in source.vertex_groups}
    body_group = source.vertex_groups['body'].index
    surface_ids = {v.index for v in source.data.vertices if any(g.group == body_group and g.weight > .5 for g in v.groups)}
    deleted = {i for i, flag in enumerate(patch['proxy']['delete_verts']) if flag}
    faces, uv_faces = [], []
    source_uv = source.data.uv_layers.active.data
    for face in source.data.polygons:
        if all(i in surface_ids for i in face.vertices) and not any(i in deleted for i in face.vertices):
            faces.append(list(face.vertices))
            uv_faces.append([tuple(source_uv[i].uv) for i in face.loop_indices])
    used = sorted({i for face in faces for i in face})
    index = {old: new for new, old in enumerate(used)}
    vertices = [coords[i].copy() for i in used]
    weights = [{groups[g.group]: g.weight for g in source.data.vertices[i].groups
                if groups[g.group] in rig.data.bones and g.weight > 0} for i in used]
    faces = [[index[i] for i in face] for face in faces]
    # MxA uses MakeHuman's Y-up coordinates; Blender uses Z-up metres.
    scale = {}
    for name, component in [('x', 0), ('y', 2), ('z', 1)]:
        a, b, distance = patch['proxy']['bounding_box'][name]
        scale[name] = abs(coords[a][component] - coords[b][component]) / distance
    patch_index, seam_count = {}, 0
    for n, (ids, factors, offset) in enumerate(patch['proxy']['fitting']):
        if factors == [1, 0, 0] and offset == [0, 0, 0] and ids[0] in index:
            patch_index[n] = index[ids[0]]
            seam_count += 1
            continue
        co = sum((coords[i] * w for i, w in zip(ids, factors)), Vector())
        co += Vector((offset[0] * scale['x'], -offset[2] * scale['z'], offset[1] * scale['y']))
        patch_index[n] = len(vertices)
        vertices.append(co)
        blend = {}
        for i, factor in zip(ids, factors):
            for group in source.data.vertices[i].groups:
                name = groups[group.group]
                if name in rig.data.bones:
                    blend[name] = blend.get(name, 0) + factor * group.weight
        blend = {k: max(0, v) for k, v in blend.items() if v > 0}
        total = sum(blend.values())
        if total <= 0:
            raise ValueError('An anatomical vertex has no skeleton weights.')
        weights.append({k: v / total for k, v in blend.items()})
    patch_start = len(faces)
    for face, uv in zip(patch['mesh']['faces'], patch['mesh']['uv_faces']):
        faces.append([patch_index[i] for i in face])
        uv_faces.append([patch['mesh']['uv_coordinates'][i] for i in uv])
    mesh = bpy.data.meshes.new('Adult continuous anatomical surface')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    body = bpy.data.objects.new('Adult_Anatomy_Surface', mesh)
    bpy.context.scene.collection.objects.link(body)
    uv = mesh.uv_layers.new(name='Body UV')
    for face, corners in zip(mesh.polygons, uv_faces):
        for loop, coord in zip(face.loop_indices, corners):
            uv.data[loop].uv = coord
    body.data.materials.append(source.data.materials[0])
    for name in rig.data.bones.keys():
        body.vertex_groups.new(name=name)
    for i, blend in enumerate(weights):
        for name, weight in blend.items():
            body.vertex_groups[name].add([i], weight, 'REPLACE')
    skinned(body, rig)
    subdivision = body.modifiers.new('Editable surface smoothing', 'SUBSURF')
    subdivision.levels = 1
    subdivision.render_levels = 2
    body.shape_key_add(name='Basis')
    # Copy genuine MPFB detail deltas to the derived surface, independent of age.
    for label, target in [('Nipple projection', 'breast/nipple-point-incr'),
                          ('Nipple diameter', 'breast/nipple-size-incr'),
                          ('Gluteal volume', 'buttocks/buttocks-volume-incr')]:
        TargetService.load_target(source, str(targets / (target + '.target.gz')), weight=0, name=label)
        key = body.shape_key_add(name=label)
        original = source.data.shape_keys.key_blocks[label]
        basis = source.data.shape_keys.key_blocks[0]
        for old, new in index.items():
            key.data[new].co += original.data[old].co - basis.data[old].co
        for n, (ids, factors, _) in enumerate(patch['proxy']['fitting']):
            new = patch_index[n]
            if new >= len(used):
                key.data[new].co += sum(((original.data[i].co - basis.data[i].co) * w
                                         for i, w in zip(ids, factors)), Vector())
        key.slider_min = -.15
        key.slider_max = .65
    # Neutral physique adjustment: local breast surface only, no skeleton scaling.
    key = body.shape_key_add(name='Breast volume')
    tips = [coords[v.index] for v in source.data.vertices
            if any(g.group == source.vertex_groups['nippleTip'].index for g in v.groups)]
    centers = [sum((v for v in tips if v.x * side > 0), Vector()) / len([v for v in tips if v.x * side > 0])
               for side in (-1, 1)]
    for v in mesh.vertices:
        center = min(centers, key=lambda c: (c - v.co).length_squared)
        d = v.co - center
        falloff = math.exp(-((d.x / .075) ** 2 + (d.z / .075) ** 2 + (d.y / .09) ** 2) * 2)
        if v.co.y < center.y + .07:
            key.data[v.index].co += Vector((d.x * .22, -.032, d.z * .15)) * falloff
    key.slider_min = -.5
    key.slider_max = .5
    # Fitted core body parts and CC0 nail meshes use MPFB's own attachment maps.
    equipped = []
    choices = [('eyes/high-poly/high-poly.mhclo', 'Eyes'),
               ('teeth/teeth_base/teeth_base.mhclo', 'Teeth'),
               ('tongue/tongue01/tongue01.mhclo', 'Tongue'),
               ('eyebrows/eyebrow001/eyebrow001.mhclo', 'Eyebrows'),
               ('eyelashes/eyelashes01/eyelashes01.mhclo', 'Eyelashes'),
               ('hair/ponytail01/ponytail01.mhclo', 'Hair')]
    for path, kind in choices:
        obj = HumanService.add_mhclo_asset(str(assets / 'makehuman_system_assets' / path), source,
                                         asset_type=kind, subdiv_levels=1)
        equipped.append(obj)
    for name in ('mindfront_nails_01_short', 'mindfront_nails_toes_01'):
        obj = HumanService.add_mhclo_asset(str(assets / 'bodyparts04/clothes' / name / (name + '.mhclo')),
                                         source, subdiv_levels=1)
        obj['body_detail'] = 'Fitted CC0 nail mesh; not clothing'
        equipped.append(obj)
    # Subtle individual body-hair strands, sampled on the actual mons surface.
    randomizer = random.Random(81018)
    hair_vertices, hair_faces, hair_weights = [], [], []
    candidates = []
    for face in mesh.polygons:
        center = face.center
        if abs(center.x) < .065 and .76 < center.z < .87 and center.y < -.055 and face.normal.y < -.45:
            candidates.append(face)
    if not candidates:
        raise ValueError('No verified front pelvic surface for the body-hair roots.')
    for _ in range(650):
        face = randomizer.choices(candidates, weights=[f.area for f in candidates])[0]
        triangle = list(face.vertices)[:3]
        a, b = randomizer.random(), randomizer.random()
        if a + b > 1:
            a, b = 1 - a, 1 - b
        bary = (a, b, 1 - a - b)
        pos = sum((mesh.vertices[i].co * w for i, w in zip(triangle, bary)), Vector())
        if (pos.x / .065) ** 2 + ((pos.z - .827) / .053) ** 2 > 1:
            continue
        normal = face.normal.normalized()
        tangent = Vector((randomizer.uniform(-.35, .35), 0, -1)).normalized()
        length = randomizer.uniform(.006, .014)
        strand_weights = {}
        for i, factor in zip(triangle, bary):
            for name, weight in weights[i].items():
                strand_weights[name] = strand_weights.get(name, 0) + factor * weight
        start = len(hair_vertices)
        for step in range(5):
            t = step / 4
            center = pos + normal * (.00025 + math.sin(t * math.pi) * .0016) + tangent * (length * t)
            center.x += math.sin(t * 7) * .0007
            radius = .000085 * (1 - .9 * t)
            for side in range(3):
                angle = side * math.tau / 3
                hair_vertices.append(center + Vector((math.cos(angle) * radius, math.sin(angle) * radius, 0)))
                hair_weights.append(strand_weights)
            if step:
                for side in range(3):
                    hair_faces.append((start + (step - 1) * 3 + side, start + (step - 1) * 3 + (side + 1) % 3,
                                       start + step * 3 + (side + 1) % 3, start + step * 3 + side))
    hair_mesh = bpy.data.meshes.new('Individual body-hair strands')
    hair_mesh.from_pydata(hair_vertices, [], hair_faces)
    hair = bpy.data.objects.new('Body_Hair', hair_mesh)
    bpy.context.scene.collection.objects.link(hair)
    skinned(hair, rig)
    mat = bpy.data.materials.new('Body hair — natural dark brown')
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.035, .016, .009, 1)
    shader.inputs['Roughness'].default_value = .65
    hair.data.materials.append(mat)
    for name in rig.data.bones.keys():
        hair.vertex_groups.new(name=name)
    for i, blend in enumerate(hair_weights):
        for name, weight in blend.items():
            hair.vertex_groups[name].add([i], weight, 'REPLACE')
    # Add local sculpt resolution in the perianal area while preserving UVs,
    # shape-key layers and deform weights via Blender's mesh subdivision.
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    body.active_shape_key_index = 0
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='VERT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    for v in mesh.vertices:
        v.select = abs(v.co.x) < .022 and .73 < v.co.z < .79 and v.co.y > -.008
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.subdivide(number_cuts=3, smoothness=0)
    bpy.ops.object.mode_set(mode='OBJECT')
    key = body.shape_key_add(name='Perianal surface detail')
    affected = 0
    for v in mesh.vertices:
        x, y, z = v.co
        r2 = (x / .0055) ** 2 + ((z - .7615) / .0055) ** 2
        if -.005 < y < .045 and r2 < 9:
            # A shallow closed surface contour, not an internal canal.
            displacement = -.0022 * math.exp(-r2 * 2) + .0005 * math.exp(-((math.sqrt(r2) - 1) / .35) ** 2)
            key.data[v.index].co.y += displacement
            affected += 1
    if affected < 8:
        raise ValueError('Insufficient local resolution for the perianal surface study.')
    key.value = .8
    key.slider_max = 1
    if len(mesh.vertices) > 18000:
        raise ValueError('Local sculpt subdivision unexpectedly affected the whole body.')
    body['perianal_detail_scope'] = 'Shallow closed external surface contour; no internal canal or medical certification.'
    # Named controls are available as ordinary Blender shape keys, without
    # installing an executable addon or enabling auto-run in the source file.
    source.hide_render = True
    source.hide_set(True)
    source['purpose'] = 'Preserved adult parametric source. Refit/rebuild derived anatomy after macro changes.'
    rig.hide_render = True
    rig.hide_set(True)
    body['adult_age_profile'] = float(age)
    body['asset_status'] = 'Neutral adult anatomical source study. Photographic realism and live speech compatibility unfinished.'
    body['anatomy_patch_licence'] = json.dumps(patch['license'])
    body['commercial_redistribution_cleared'] = False
    body['source_profile'] = source.get('body_profile', '{}')
    body['anatomy_surface_faces'] = len(faces) - patch_start
    body['welded_boundary_vertices'] = seam_count
    bpy.context.scene['body_hair_visibility'] = 'Toggle Body_Hair in the Outliner; it follows the body rig.'
    for image in bpy.data.images:
        if image.source == 'FILE' and not image.packed_file:
            image.pack()
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    # Save a usable full-body front view and expose its ordinary shape controls.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                space.overlay.show_overlays = False
                space.shading.type = 'MATERIAL'
                space.region_3d.view_location = (0, 0, .80)
                space.region_3d.view_distance = 2.35
                space.region_3d.view_rotation = Vector((0, 1, 0)).to_track_quat('-Z', 'Y')
                space.region_3d.view_perspective = 'ORTHO'
            elif area.type == 'PROPERTIES':
                area.spaces.active.context = 'DATA'
    notes = bpy.data.texts.new('ANATOMY STUDY — status and sources')
    notes.write('Adult neutral modelling study. Original source preserved. Continuous welded external anatomy; '
                'nipples, navel, fitted eyes/teeth/tongue/brows/lashes/hair/nails and weighted body hair. '
                'Shape keys: Breast volume, Nipple projection, Nipple diameter, Gluteal volume, Perianal surface detail. '
                'External patch source: makehumancommunity/mhx2-makehuman-exchange, vulva.mxa. '
                'Embedded licence says AGPL3; author website describes extra content as CC0. '
                'Keep local pending redistribution licence clarification; not cleared for product distribution. '
                'Perianal detail is a shallow closed external contour, not an internal canal. '
                'No internal anatomy, surgical accuracy, photographic finish, '
                'extreme-pose corrective shapes or browser mouth-shape compatibility certification.\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    report = {'status': 'anatomical_source_study', 'file': destination.name, 'adult_age_profile': float(age),
              'vertices': len(mesh.vertices), 'faces': len(mesh.polygons), 'bones': len(rig.data.bones),
              'anatomy_patch_faces': len(faces) - patch_start, 'welded_seam_vertices': seam_count,
              'body_hair_strands': len(hair_vertices) // 15,
              'fitted_parts': [o.name for o in equipped], 'shape_controls': [k.name for k in body.data.shape_keys.key_blocks][1:],
              'patch_sha256': hashlib.sha256(patch_path.read_bytes()).hexdigest(),
              'patch_licence': patch['license'], 'commercial_redistribution_cleared': False,
              'photographic_realism_verified': False, 'browser_face_ready': False,
              'extreme_pose_correctives_verified': False, 'perianal_contour_vertices': affected,
              'perianal_detail_medically_verified': False}
    (out / 'anatomy-study-report.json').write_text(json.dumps(report, indent=2))
    print('ANATOMY_STUDY_SAVED', json.dumps(report))


if __name__ == '__main__':
    main()
