"""Weld the original CC0 head/body boundary and remove coincident faces."""
import json
from pathlib import Path
import sys

import bpy
import bmesh

root=Path(sys.argv[sys.argv.index('--')+1]).resolve();out=root/'.runtime/character-workshop'
source=out/'Moneypenny-Free-Surface-v16.blend';candidate=out/'Moneypenny-Free-Surface-v16.glb'
if source.exists() or candidate.exists():raise SystemExit('Existing welded candidate preserved')
bpy.ops.wm.open_mainfile(filepath=str(out/'Moneypenny-Free-Surface-v14.blend'))
rig=bpy.data.objects['mixamo_vitruvian'];head=bpy.data.objects['Moneypenny_Face']
body=next(o for o in bpy.data.objects if o.type=='MESH' and any(m.name=='VitBody' for m in o.data.materials))
with bpy.data.libraries.load(str(out/'Moneypenny-Free-Surface-v13.blend'),link=False) as (available,loaded):loaded.objects=[body.name]
replacement=loaded.objects[0];bpy.data.objects.remove(body,do_unlink=True);bpy.context.scene.collection.objects.link(replacement);replacement.parent=rig
for modifier in replacement.modifiers:
 if modifier.type=='ARMATURE':modifier.object=rig
for obj in bpy.context.selected_objects:obj.select_set(False)
head.select_set(True);replacement.select_set(True);bpy.context.view_layer.objects.active=head
bpy.ops.object.join()
head.active_shape_key_index=0
before=len(head.data.vertices)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.remove_doubles(threshold=.00003)
bm=bmesh.from_edit_mesh(head.data);seen={};duplicates=[]
for face in bm.faces:
 signature=frozenset(face.verts)
 if signature in seen:duplicates.append(face)
 else:seen[signature]=face
removed=len(duplicates)
if duplicates:bmesh.ops.delete(bm,geom=duplicates,context='FACES_ONLY')
bmesh.update_edit_mesh(head.data);bpy.ops.object.mode_set(mode='OBJECT')
welded=before-len(head.data.vertices)
# Every facial key remains in the joined full-body mesh. Unchanged body vertices
# receive zero speech deltas; UV loops retain the correct source material atlas.
head['surfaceRole']='speaking-face'
for mat in bpy.data.materials:
 if mat.name=='Radial mapped natural iris':
  shader=mat.node_tree.nodes.get('Principled BSDF');input=shader.inputs['Base Color']
  if input.links:
   previous=input.links[0].from_socket;mix=mat.node_tree.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(.3,.3,.3,1)
   mat.node_tree.links.new(previous,mix.inputs[1]);mat.node_tree.links.new(mix.outputs[0],input)
# Restrained hair normal response; previous full-resolution groom is preserved.
hair=bpy.data.objects['VitHair']
for obj in bpy.context.selected_objects:obj.select_set(False)
hair.select_set(True);bpy.context.view_layer.objects.active=hair
modifier=hair.modifiers.new('Browser combined-mesh budget','DECIMATE');modifier.ratio=.86;modifier.use_collapse_triangulate=True
bpy.ops.object.modifier_apply(modifier=modifier.name)
parts=[o for o in bpy.data.objects if o.type=='MESH' and o.parent==rig and not o.hide_render]
for obj in bpy.context.selected_objects:obj.select_set(False)
rig.select_set(True)
for obj in parts:obj.hide_set(False);obj.select_set(True)
bpy.context.view_layer.objects.active=rig
rig['surface_revision']='free-surface-v16 — welded head/body study'
bpy.ops.export_scene.gltf(filepath=str(candidate),export_format='GLB',use_selection=True,export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
if candidate.stat().st_size>80*1024*1024:raise ValueError('Welded candidate exceeds budget')
scene=bpy.context.scene;scene.cycles.samples=64;scene.render.resolution_x=760;scene.render.resolution_y=960
scene.render.filepath=str(root/'verification/free-surface-v16-portrait.png')
bpy.ops.wm.save_as_mainfile(filepath=str(source));bpy.ops.render.render(write_still=True)
report={'revision':'free-surface-v16','bytes':candidate.stat().st_size,'welded_vertices':welded,'duplicate_faces_removed':removed,
        'head_shapes_retained':len(head.data.shape_keys.key_blocks)-1,'photographic_realism_verified':False,'actual_browser_acceptance':False,'cost':0}
(out/'free-surface-v16-report.json').write_text(json.dumps(report,indent=2))
print('FREE_SURFACE_WELD_COMPLETE',json.dumps(report),flush=True)
