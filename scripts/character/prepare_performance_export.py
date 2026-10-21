"""Bake skin maps, inspect the face and export a private studio candidate.

Does not load/upload the resulting character into a browser.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

root = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
out = root / '.runtime/character-workshop'
destination = out / 'Moneypenny-Performance-Export-v6.blend'
candidate = out / 'Moneypenny-Performance-Candidate-v6.glb'
if destination.exists() or candidate.exists():
    raise SystemExit('Existing prepared export preserved.')
bpy.ops.wm.open_mainfile(filepath=str(out / 'Moneypenny-Performance-Final-Fit-v3.blend'))
body = bpy.data.objects['Adult_Anatomy_Surface']
rig = bpy.data.objects['Adult_Body_Rig']
parts = [obj for obj in bpy.data.objects if obj.parent == rig and obj.type == 'MESH' and not obj.hide_render]
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.cycles.adaptive_threshold = .06
scene.render.image_settings.file_format = 'PNG'
reports = {'facial_shapes': {}, 'corrective_driver_values': {}, 'local_only': True}
for name in ['viseme_aa', 'viseme_PP', 'viseme_FF', 'eyeBlinkLeft', 'eyeBlinkRight', 'mouthSmileLeft', 'jawOpen']:
    key = body.data.shape_keys.key_blocks[name]
    delta = max((a.co - b.co).length for a, b in zip(key.data, body.data.shape_keys.key_blocks[0].data))
    reports['facial_shapes'][name] = {'max_delta_m': delta, 'finite': math.isfinite(delta),
                                    'attached_meshes': [obj.name for obj in parts if obj.data.shape_keys and name in obj.data.shape_keys.key_blocks]}
    if not math.isfinite(delta) or delta < 1e-6:
        raise ValueError('Missing/invalid facial deformation: ' + name)
for suffix in ('Left', 'Right'):
    rig.pose.bones['mixamorig:' + suffix + 'ForeArm'].rotation_mode = 'XYZ'
    rig.pose.bones['mixamorig:' + suffix + 'ForeArm'].rotation_euler.z = 1.3
    rig.pose.bones['mixamorig:' + suffix + 'Leg'].rotation_mode = 'XYZ'
    rig.pose.bones['mixamorig:' + suffix + 'Leg'].rotation_euler.x = 1.3
bpy.context.view_layer.update()
for key in body.data.shape_keys.key_blocks:
    if key.name.startswith('corrective_'):
        reports['corrective_driver_values'][key.name] = key.value
for bone in rig.pose.bones:
    bone.rotation_euler = (0, 0, 0)
bpy.context.view_layer.update()
print('PERFORMANCE_FACE_CHECKS', json.dumps(reports), flush=True)
# Bake the actual procedural roughness/bump from this mesh into browser PBR maps.
for obj in bpy.context.selected_objects:
    obj.select_set(False)
body.hide_set(False)
body.select_set(True)
bpy.context.view_layer.objects.active = body
skin = body.data.materials[0]
nodes, links = skin.node_tree.nodes, skin.node_tree.links
shader = nodes.get('Principled BSDF')
output = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
roughness_input = shader.inputs['Roughness']
roughness_source = roughness_input.links[0].from_socket
emission = nodes.new('ShaderNodeEmission')
links.new(roughness_source, emission.inputs['Color'])
links.new(emission.outputs[0], output.inputs['Surface'])
target = nodes.new('ShaderNodeTexImage')
rough = bpy.data.images.new('Skin roughness — baked from source', width=2048, height=2048, alpha=False)
rough.colorspace_settings.name = 'Non-Color'
target.image = rough
nodes.active = target
scene.cycles.samples = 1
scene.render.bake.margin = 8
bpy.ops.object.bake(type='EMIT')
rough.filepath_raw = str(out / 'performance-skin-roughness.png')
rough.file_format = 'PNG'
rough.save()
rough.pack()
links.new(shader.outputs[0], output.inputs['Surface'])
nodes.remove(emission)
links.new(target.outputs['Color'], shader.inputs['Roughness'])
normal = bpy.data.images.new('Skin normal — baked surface', width=2048, height=2048, alpha=False)
normal.colorspace_settings.name = 'Non-Color'
normal_target = nodes.new('ShaderNodeTexImage')
normal_target.image = normal
nodes.active = normal_target
bpy.ops.object.bake(type='NORMAL')
normal.filepath_raw = str(out / 'performance-skin-normal.png')
normal.file_format = 'PNG'
normal.save()
normal.pack()
normal_node = nodes.new('ShaderNodeNormalMap')
links.new(normal_target.outputs['Color'], normal_node.inputs['Color'])
links.new(normal_node.outputs['Normal'], shader.inputs['Normal'])
# Morph values must be neutral for export; preserve authored body detail values.
for obj in parts:
    if obj.data.shape_keys:
        for key in obj.data.shape_keys.key_blocks:
            if key.name.startswith('viseme_') or key.name in reports['facial_shapes'] or key.name.startswith('eye') or key.name.startswith('mouth') or key.name.startswith('jaw'):
                key.value = 0
    for modifier in obj.modifiers:
        if modifier.type in ('SUBSURF', 'SOLIDIFY'):
            modifier.show_viewport = False
            modifier.show_render = False
# Keep the unbaked source scene separate. Bone names and deform groups are
# renamed consistently in this export copy for TalkingHead's exact contract.
renames = {b.name: b.name.replace('mixamorig:', '') for b in rig.data.bones}
for obj in parts:
    for group in obj.vertex_groups:
        if group.name in renames:
            group.name = renames[group.name]
for bone in list(rig.data.bones):
    bone.name = renames[bone.name]
for obj in bpy.context.selected_objects:
    obj.select_set(False)
rig.hide_set(False)
rig.select_set(True)
for obj in parts:
    obj.hide_set(False)
    obj.select_set(True)
    obj['production_candidate'] = True
rig['commercial_redistribution_cleared'] = False
rig['source_scope'] = 'Local performance candidate; no photographic or universal-pose certification.'
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=str(candidate), export_format='GLB', use_selection=True,
                          export_animations=False, export_morph=True, export_skins=True,
                          export_extras=True, export_apply=False)
if candidate.stat().st_size > 80 * 1024 * 1024:
    raise ValueError('Candidate exceeds the current studio import limit; preserved for optimisation.')
reports['glb_bytes'] = candidate.stat().st_size
reports['skin_maps'] = ['2048px colour (CC0 source)', '2048px baked procedural roughness', '2048px baked normal']
reports['photographic_realism_verified'] = False
reports['live_browser_acceptance'] = False
(out / 'performance-export-report.json').write_text(json.dumps(reports, indent=2))
# Native review scene with smoothing retained; this does not alter the GLB.
for obj in parts:
    for modifier in obj.modifiers:
        if modifier.type in ('SUBSURF', 'SOLIDIFY'):
            modifier.show_viewport = True
            modifier.show_render = True
rig.hide_set(True)
camera_data = bpy.data.cameras.new('Portrait review')
camera = bpy.data.objects.new('Portrait review', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'PERSP'
camera_data.lens = 85
camera.location = (0, -1.5, 1.50)
camera.rotation_euler = (Vector((0, -.025, 1.43)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.resolution_x = 760
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.cycles.samples = 32
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
def expression(name=None, value=0):
    for obj in parts:
        if obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:
                if key.name.startswith('viseme_') or key.name.startswith('eyeBlink'):
                    key.value = value if key.name == name else 0
for label, name, value in [('portrait', None, 0), ('mouth-aa', 'viseme_aa', .65), ('blink', 'eyeBlinkLeft', 1)]:
    expression(name, value)
    scene.render.filepath = str(root / 'verification' / ('performance-' + label + '.png'))
    bpy.ops.render.render(write_still=True)
expression()
print('PERFORMANCE_EXPORT_READY', candidate, candidate.stat().st_size, flush=True)
