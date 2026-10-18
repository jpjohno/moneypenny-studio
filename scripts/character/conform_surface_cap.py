"""Remove coarse hair-cap ridges while retaining original rig and UV data."""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
out=root/'.runtime/character-workshop'
destination=out/'Moneypenny-Surface-Look-v9.blend'
candidate=out/'Moneypenny-Performance-Candidate-v9.glb'
if destination.exists() or candidate.exists(): raise SystemExit('Existing v9 preserved')
bpy.ops.wm.open_mainfile(filepath=str(out/'Moneypenny-Surface-Look-v8.blend'))
scene=bpy.context.scene
rig=bpy.data.objects['Adult_Body_Rig']
body=bpy.data.objects['Adult_Anatomy_Surface']
cap=next(o for o in bpy.data.objects if o.parent==rig and '.ponytail01' in o.name)
tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
changed=0
for vertex in cap.data.vertices:
 point=cap.matrix_world@vertex.co
 if point.z<1.48: continue
 nearest,normal,_,distance=tree.find_nearest(point)
 if nearest is None or distance>.07: continue
 mix=min(1,max(0,(point.z-1.48)/.035))
 target=nearest+normal*.004
 offset=cap.matrix_world.inverted()@(point.lerp(target,mix))-vertex.co
 vertex.co+=offset
 if cap.data.shape_keys:
  for shape in cap.data.shape_keys.key_blocks: shape.data[vertex.index].co+=offset
 changed+=1
cap.data.update()
for material in cap.data.materials:
 shader=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 for link in list(shader.inputs['Base Color'].links): material.node_tree.links.remove(link)
 shader.inputs['Base Color'].default_value=(.035,.014,.006,1)
 shader.inputs['Roughness'].default_value=.62
 shader.inputs['Specular IOR Level'].default_value=.12
# Keep brow microgeometry from hovering outside the expression surface.
parts=[o for o in bpy.data.objects if o.parent==rig and o.type=='MESH' and not o.hide_render]
for obj in bpy.context.selected_objects: obj.select_set(False)
rig.hide_set(False)
rig.select_set(True)
for obj in parts:
 obj.hide_set(False)
 obj.select_set(True)
 for modifier in obj.modifiers:
  if modifier.type in ('SUBSURF','SOLIDIFY'): modifier.show_viewport=False;modifier.show_render=False
bpy.context.view_layer.objects.active=rig
rig['surface_revision']='v9 — fitted scalp cap, full-scalp groom, spatial skin maps and expression-linked brows'
bpy.ops.export_scene.gltf(filepath=str(candidate),export_format='GLB',use_selection=True,export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
if candidate.stat().st_size>80*1024*1024: raise ValueError('Candidate exceeds browser limit')
for obj in parts:
 for modifier in obj.modifiers:
  if modifier.type=='SUBSURF': modifier.show_render=True
scene.cycles.samples=96
scene.cycles.use_denoising=True
scene.render.resolution_x=900
scene.render.resolution_y=1125
scene.render.filepath=str(root/'verification/surface-v9-portrait.png')
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
bpy.ops.render.render(write_still=True)
scene.camera.data.type='ORTHO'
scene.camera.data.ortho_scale=1.8
scene.camera.location=(.3,-3,.85)
scene.camera.rotation_euler=(Vector((0,0,.8))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=640
scene.render.resolution_y=900
scene.cycles.samples=48
scene.render.filepath=str(root/'verification/surface-v9-full-body.png')
bpy.ops.render.render(write_still=True)
report={'revision':'v9','fitted_cap_vertices':changed,'bytes':candidate.stat().st_size,
        'photographic_realism_verified':False,'live_browser_acceptance':False,
        'source':'Moneypenny-Surface-Look-v8.blend','previous_sources_preserved':True,
        'views':['verification/surface-v9-portrait.png','verification/surface-v9-full-body.png']}
(out/'surface-v9-report.json').write_text(json.dumps(report,indent=2))
print('CAP_FIT_COMPLETE',json.dumps(report),flush=True)
