"""Build a dressed performance candidate, preserving the anatomical study.

Native authoring only: no browser upload, avatar replacement or public asset
distribution. All non-code assets retain their source notices in the blend.
"""
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).parent))
from refine_body import rest_coordinates


def install_data(assets, user_data, packs):
    """Install only absent inert data files; reject conflicting artist edits."""
    for pack in packs:
        source = assets / pack
        for item in source.rglob('*'):
            if not item.is_file():
                continue
            relative = item.relative_to(source)
            destination = user_data / relative
            if destination.exists():
                if hashlib.sha256(destination.read_bytes()).digest() != hashlib.sha256(item.read_bytes()).digest():
                    raise ValueError('Existing asset differs and was preserved: ' + str(destination))
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, destination)


def add_eye_bones(source, rig, eyes):
    coords = rest_coordinates(source)
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for side, helper in [('Left', 'helper-l-eye'), ('Right', 'helper-r-eye')]:
        group = source.vertex_groups[helper].index
        points = [coords[v.index] for v in source.data.vertices if any(g.group == group for g in v.groups)]
        center = sum(points, Vector()) / len(points)
        bone = rig.data.edit_bones.new(side + 'Eye')
        bone.head = center
        bone.tail = center + Vector((0, -.02, 0))
        bone.parent = rig.data.edit_bones['mixamorig:Head']
    bpy.ops.object.mode_set(mode='OBJECT')
    for vertex in eyes.data.vertices:
        for group in list(vertex.groups):
            eyes.vertex_groups[group.group].remove([vertex.index])
    for side in ('Left', 'Right'):
        group = eyes.vertex_groups.get(side + 'Eye') or eyes.vertex_groups.new(name=side + 'Eye')
        group.add([v.index for v in eyes.data.vertices if (v.co.x >= 0) == (side == 'Left')], 1, 'REPLACE')


def corrective_keys(body, rig):
    """Small rest-space volume corrections; driven by measured joint bend."""
    specs = [('elbow', 'Left', 'LeftArm', 'LeftForeArm', 'LeftHand'),
             ('elbow', 'Right', 'RightArm', 'RightForeArm', 'RightHand'),
             ('knee', 'Left', 'LeftUpLeg', 'LeftLeg', 'LeftFoot'),
             ('knee', 'Right', 'RightUpLeg', 'RightLeg', 'RightFoot')]
    result = []
    for kind, side, a, b, c in specs:
        joint = rig.data.bones['mixamorig:' + b].head_local
        axis = (rig.data.bones['mixamorig:' + c].head_local - joint).normalized()
        name = 'corrective_' + kind + '_' + side[0]
        key = body.shape_key_add(name=name)
        count = 0
        for vertex in body.data.vertices:
            delta = vertex.co - joint
            along = delta.dot(axis)
            radial = delta - axis * along
            width = .035 if kind == 'elbow' else .045
            if delta.length < width * 2 and radial.length > .006:
                offset = radial.normalized() * (.0025 if kind == 'elbow' else .0035)
                key.data[vertex.index].co += offset * math.exp(-(along / width) ** 2 * 2)
                count += 1
        if count < 8:
            raise ValueError('Insufficient vertices for ' + name)
        key.slider_max = 1
        driver = key.driver_add('value').driver
        driver.type = 'SCRIPTED'
        for letter, bone in [('a', a), ('b', b), ('c', c)]:
            for axis_name in ('x', 'y', 'z'):
                variable = driver.variables.new()
                variable.name = letter + axis_name
                variable.type = 'TRANSFORMS'
                target = variable.targets[0]
                target.id = rig
                target.bone_target = 'mixamorig:' + bone
                target.transform_type = 'LOC_' + axis_name.upper()
                target.transform_space = 'WORLD_SPACE'
        dot = '+'.join(f'(a{x}-b{x})*(c{x}-b{x})' for x in 'xyz')
        la = '+'.join(f'(a{x}-b{x})**2' for x in 'xyz')
        lc = '+'.join(f'(c{x}-b{x})**2' for x in 'xyz')
        driver.expression = f'min(1,max(0,3.14159265-acos(min(1,max(-1,({dot})/sqrt(({la})*({lc}))))))/1.6)'
        result.append({'name': name, 'bones': [a, b, c], 'vertices': count})
    return result


def main():
    root = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    out = root / '.runtime/character-workshop'
    destination = out / 'Moneypenny-Performance-Character.blend'
    if destination.exists():
        raise SystemExit('Existing performance scene preserved: ' + str(destination))
    bpy.ops.wm.open_mainfile(filepath=str(out / 'Moneypenny-Adult-Anatomy-Study-v3.blend'))
    from bl_ext.user_default.mpfb.services.faceservice import FaceService, META_VISEMES, ARKIT_FACEUNITS
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    from bl_ext.user_default.mpfb.services.locationservice import LocationService
    from bl_ext.user_default.mpfb.services.assetservice import AssetService
    assets = root / '.runtime/character-tools/assets'
    finish_manifest = json.loads(Path(__file__).with_name('finish-assets.json').read_text())
    for pack in finish_manifest['packs']:
        if hashlib.sha256((assets / (pack['name'] + '.zip')).read_bytes()).hexdigest() != pack['sha256']:
            raise ValueError('Asset archive checksum mismatch: ' + pack['name'])
    install_data(assets, Path(LocationService.get_user_data()),
                 ['makehuman_system_assets', 'bodyparts04', 'skins01', 'hair02', 'visemes02', 'faceunits01'])
    AssetService.invalidate_pack_metadata_cache()
    source = bpy.data.objects['Adult_Body_Source']
    body = bpy.data.objects['Adult_Anatomy_Surface']
    rig = bpy.data.objects['Adult_Body_Rig']
    FaceService.load_targets(source, load_microsoft_visemes=False, load_meta_visemes=True, load_arkit_faceunits=True)
    FaceService.interpolate_targets(source)
    coords = rest_coordinates(source)
    tree = KDTree(len(coords))
    for i, co in enumerate(coords):
        tree.insert(co, i)
    tree.balance()
    mapping = [(v.index, tree.find(v.co)) for v in body.data.vertices if v.co.z > 1.2]
    original_basis = source.data.shape_keys.key_blocks[0]
    targets = list(META_VISEMES) + list(ARKIT_FACEUNITS)
    for name in targets:
        original = source.data.shape_keys.key_blocks[name]
        key = body.shape_key_add(name=name)
        for index, (_, source_index, distance) in mapping:
            if distance < .00001:
                key.data[index].co += original.data[source_index].co - original_basis.data[source_index].co
    eyes = next(o for o in bpy.data.objects if o.name.startswith('Adult_Body_Source.high-poly'))
    add_eye_bones(source, rig, eyes)
    # Replace only the derived scene's old ponytail with an authored, normal-mapped hair asset.
    for obj in bpy.data.objects:
        if obj.name.startswith('Adult_Body_Source.ponytail01'):
            obj.hide_render = True
            obj.hide_set(True)
    hair = HumanService.add_mhclo_asset(str(assets / 'hair02/hair/elvs_lara_hair/elvs_lara_hair.mhclo'), source,
                                      asset_type='Hair', subdiv_levels=0)
    hair['attribution'] = 'Lara hair by Elvaerwyn, CC-BY; MakeHuman hair02 pack. Source notices retained.'
    for mat in hair.data.materials:
        if mat and mat.use_nodes:
            shader = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if shader:
                shader.inputs['Roughness'].default_value = .42
                anisotropy = shader.inputs.get('Anisotropic')
                if anisotropy:
                    anisotropy.default_value = .55
    # The source skin remains a real, attributed 2K colour texture. Pores/roughness
    # are procedural look development; they are not represented as scan data.
    skin = body.data.materials[0].copy()
    skin.name = 'Performance skin — textured, subsurface and microdetail'
    shader = skin.node_tree.nodes.get('Principled BSDF')
    texture = next(n for n in skin.node_tree.nodes if n.type == 'TEX_IMAGE')
    texture.image = bpy.data.images.load(str(assets / 'skins01/skins/toigo_light_skin_with_natural_makeup/young_lightskinned_female_diffuse4.png'), check_existing=True)
    shader.inputs['Roughness'].default_value = .46
    shader.inputs['Subsurface Weight'].default_value = .12
    shader.inputs['Subsurface Scale'].default_value = .002
    noise = next(n for n in skin.node_tree.nodes if n.type == 'TEX_NOISE')
    remap = skin.node_tree.nodes.new('ShaderNodeMapRange')
    remap.inputs['To Min'].default_value = .38
    remap.inputs['To Max'].default_value = .56
    skin.node_tree.links.new(noise.outputs['Fac'], remap.inputs['Value'])
    skin.node_tree.links.new(remap.outputs['Result'], shader.inputs['Roughness'])
    body.data.materials.clear()
    body.data.materials.append(skin)
    suit = HumanService.add_mhclo_asset(str(assets / 'makehuman_system_assets/clothes/female_elegantsuit01/female_elegantsuit01.mhclo'), source, subdiv_levels=1)
    suit.name = 'Office_Blouse_And_Skirt'
    suit['wardrobeSlot'] = 'outfit'
    suit['wardrobeLabel'] = 'Fitted office blouse and skirt'
    shoes = HumanService.add_mhclo_asset(str(assets / 'makehuman_system_assets/clothes/shoes03/shoes03.mhclo'), source, subdiv_levels=1)
    shoes.name = 'Office_Ankle_Shoes'
    shoes['wardrobeSlot'] = 'shoes'
    shoes['wardrobeLabel'] = 'Fitted black ankle shoes'
    for obj in (suit, shoes):
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE':
                modifier.use_deform_preserve_volume = True
        thickness = obj.modifiers.new('Garment edge thickness', 'SOLIDIFY')
        thickness.thickness = .0008
        thickness.offset = 1
    # Clothing follows the genuine source attachment map, then receives a small
    # outward fitting allowance. This is a fitted skin, not simulated dressing.
    for vertex in suit.data.vertices:
        vertex.co += vertex.normal * .0015
    corrections = corrective_keys(body, rig)
    # Preserve the complete anatomy when fitting: source-only garment masks must
    # never be copied onto the anatomical surface.
    source.hide_render = True
    source.hide_set(True)
    rig.hide_set(True)
    for name, energy in [('Key', 250), ('Fill', 85), ('Rim', 200)]:
        bpy.data.objects[name].data.energy = energy
    scene = bpy.context.scene
    scene.view_settings.view_transform = 'AgX'
    scene['performance_candidate_status'] = 'Textured and dressed source with facial morphs and moderate pose correctives; photographic realism and live browser acceptance unverified.'
    body['facial_target_count'] = len(targets)
    body['skin_attribution'] = 'Natural makeup skin by MargaretToigo, skins01 CC0. 2048px colour; procedural pores/roughness, not photogrammetry.'
    body['body_corrective_scope'] = 'Small joint-bend-driven rest-space volume corrections, not complete artist-sculpted pose-space deformation.'
    notes = bpy.data.texts.new('PERFORMANCE CANDIDATE — status and attribution')
    notes.write(json.dumps({'skin': body['skin_attribution'], 'hair': hair['attribution'],
                            'facial_targets': targets, 'correctives': corrections,
                            'anatomy_licence': body.get('anatomy_patch_licence'),
                            'commercial_redistribution_cleared': False,
                            'limitations': ['Not a photographed or scanned person', 'No cloth dynamics or dressing simulation',
                                            'Artist pose corrections and extreme-pose acceptance unfinished',
                                            'GLB export and actual speaking/browser acceptance still require verification']}, indent=2))
    for image in bpy.data.images:
        if image.source == 'FILE' and not image.packed_file:
            image.pack()
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    report = {'file': destination.name, 'facial_targets': targets, 'facial_target_count': len(targets),
              'correctives': corrections, 'bones': len(rig.data.bones), 'hair': hair.name,
              'garments': [suit.name, shoes.name], 'skin': body['skin_attribution'],
              'commercial_redistribution_cleared': False, 'photographic_realism_verified': False,
              'live_browser_acceptance': False}
    (out / 'performance-candidate-report.json').write_text(json.dumps(report, indent=2))
    print('PERFORMANCE_CANDIDATE_SAVED', json.dumps(report))


if __name__ == '__main__':
    main()
