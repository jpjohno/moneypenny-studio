"""Restore the continuous source neck and hide only duplicated head-neck faces."""
import json
from pathlib import Path
import sys
import bpy

root=Path(sys.argv[sys.argv.index('--')+1]).resolve();out=root/'.runtime/character-workshop'
source=out/'Moneypenny-Free-Surface-v15.blend';candidate=out/'Moneypenny-Free-Surface-v15.glb'
if source.exists() or candidate.exists(): raise SystemExit('Existing seam-reviewed copy preserved')
bpy.ops.wm.open_mainfile(filepath=str(out/'Moneypenny-Free-Surface-v14.blend'))
rig=bpy.data.objects['mixamo_vitruvian'];head=bpy.data.objects['Moneypenny_Face']
old=next(o for o in bpy.data.objects if o.type=='MESH' and any(m.name=='VitBody' for m in o.data.materials))
with bpy.data.libraries.load(str(out/'Moneypenny-Free-Surface-v13.blend'),link=False) as (available,loaded):
 loaded.objects=[old.name]
restored=loaded.objects[0];bpy.data.objects.remove(old,do_unlink=True)
bpy.context.scene.collection.objects.link(restored)
restored.parent=rig
for modifier in restored.modifiers:
 if modifier.type=='ARMATURE':modifier.object=rig
# The duplicate head-neck surface stays in the source so every facial key is
# preserved. An explicit cutout material removes its overlapping render faces.
cutout=bpy.data.materials.new('Duplicate neck surface — hidden');cutout.use_nodes=True
shader=cutout.node_tree.nodes.get('Principled BSDF');shader.inputs['Alpha'].default_value=0
cutout.surface_render_method='DITHERED'
head.data.materials.append(cutout);hidden=0
for polygon in head.data.polygons:
 if all(head.data.vertices[i].co.z<1.503 for i in polygon.vertices):
  polygon.material_index=len(head.data.materials)-1;hidden+=1
# Keep the original iris detail with a darker natural brown response.
material=bpy.data.materials['Radial mapped natural iris'];nodes,links=material.node_tree.nodes,material.node_tree.links
shader=nodes.get('Principled BSDF');input=shader.inputs['Base Color']
if input.links:
 previous=input.links[0].from_socket;mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(.28,.28,.28,1)
 links.new(previous,mix.inputs[1]);links.new(mix.outputs[0],input)
shader.inputs['Coat Weight'].default_value=.45;shader.inputs['Specular IOR Level'].default_value=.2
head.data.shape_keys.key_blocks['Eyes_Closed_Max'].value=.08
parts=[o for o in bpy.data.objects if o.type=='MESH' and o.parent==rig and not o.hide_render]
for obj in bpy.context.selected_objects:obj.select_set(False)
rig.select_set(True)
for obj in parts:obj.hide_set(False);obj.select_set(True)
bpy.context.view_layer.objects.active=rig
rig['surface_revision']='free-surface-v15 — free CC0 surface study, seam and eye review'
bpy.ops.export_scene.gltf(filepath=str(candidate),export_format='GLB',use_selection=True,export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
if candidate.stat().st_size>80*1024*1024:raise ValueError('Candidate exceeds browser limit')
scene=bpy.context.scene
scene.camera.data.type='PERSP';scene.camera.data.lens=85
from mathutils import Vector
scene.camera.location=(.17,-1.22,1.68);scene.camera.rotation_euler=(Vector((0,0,1.58))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.cycles.samples=96;scene.render.resolution_x=760;scene.render.resolution_y=960
scene.render.filepath=str(root/'verification/free-surface-v15-portrait.png')
bpy.ops.wm.save_as_mainfile(filepath=str(source));bpy.ops.render.render(write_still=True)
scene.camera.data.type='ORTHO';scene.camera.data.ortho_scale=1.95
scene.camera.location=(.25,-3,.95);scene.camera.rotation_euler=(Vector((0,0,.87))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=640;scene.render.resolution_y=900;scene.cycles.samples=48
scene.render.filepath=str(root/'verification/free-surface-v15-full-body.png');bpy.ops.render.render(write_still=True)
report={'revision':'free-surface-v15','bytes':candidate.stat().st_size,'duplicate_neck_faces_hidden':hidden,
        'photographic_realism_verified':False,'actual_browser_acceptance':False,'cost':0,
        'source_surface_preserved':True,'extreme_poses_verified':False,'spring_hair_simulation_ported':False}
(out/'free-surface-v15-report.json').write_text(json.dumps(report,indent=2))
print('FREE_SURFACE_SEAM_COMPLETE',json.dumps(report),flush=True)
