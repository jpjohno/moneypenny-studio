"""Correct the free study's neck overlap and add expression-linked facial hair."""
import json
import math
from pathlib import Path
import random
import sys

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
out=root/'.runtime/character-workshop'
source=out/'Moneypenny-Free-Surface-v14.blend'
candidate=out/'Moneypenny-Free-Surface-v14.glb'
if source.exists() or candidate.exists(): raise SystemExit('Existing refined free study preserved')
bpy.ops.wm.open_mainfile(filepath=str(out/'Moneypenny-Free-Surface-v13.blend'))
rig=bpy.data.objects['mixamo_vitruvian']
head=bpy.data.objects['Moneypenny_Face']
head['surfaceRole']='speaking-face'
body=next(o for o in bpy.data.objects if o.type=='MESH' and any(m.name=='VitBody' for m in o.data.materials))
bm=bmesh.new();bm.from_mesh(body.data)
remove=[face for face in bm.faces if all(v.co.z>1.465 and abs(v.co.x)<.10 for v in face.verts)]
removed=len(remove);bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(body.data);bm.free();body.data.update()
# True dark pupils and softer sclera are needed with the ordinary PBR eyes.
sclera=bpy.data.materials['Optical off-white sclera']
shader=sclera.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.40,.38,.36,1)
pupil=bpy.data.materials.new('Natural pupil');pupil.use_nodes=True
shader=pupil.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.001,.0008,.0005,1);shader.inputs['Roughness'].default_value=.08;shader.inputs['Coat Weight'].default_value=.8
for name in ['LeftEye','RightEye']:
 eye=bpy.data.objects[name+'_Optical_Eye'];center=rig.data.bones[name].head_local
 eye.data.materials.append(pupil)
 for polygon in eye.data.polygons:
  point=sum((eye.data.vertices[i].co-center for i in polygon.vertices),Vector())/len(polygon.vertices)
  if point.y<0 and math.hypot(point.x,point.z)<.002: polygon.material_index=2
# Root brow hairs on the actual forehead. No disconnected painted brow line.
tree=BVHTree.FromObject(head,bpy.context.evaluated_depsgraph_get())
rng=random.Random(2026101814)
vertices,faces=[],[]
def filament(points,width):
 start=len(vertices)
 for i,point in enumerate(points):
  radius=width*(1-.92*i/(len(points)-1))
  vertices.extend((point+Vector((radius,0,0)),point-Vector((radius,0,0))))
  if i: faces.append((start+(i-1)*2,start+i*2,start+i*2+1,start+(i-1)*2+1))
for side in [-1,1]:
 for n in range(550):
  t=rng.random();x=side*(.014+.045*t);z=1.655+.008*math.sin(t*math.pi)-.004*t+rng.uniform(-.0013,.0013)
  hit,normal,_,_=tree.ray_cast(Vector((x,-.4,z)),Vector((0,1,0)))
  if hit is None: continue
  base=hit+normal*.00065
  length=rng.uniform(.0016,.0033)
  points=[base+Vector((side*length*u*.8,-.00045*math.sin(u*math.pi),length*u*.65)) for u in [0,.33,.66,1]]
  filament(points,.000055)
 for eye_name in ['LeftEye' if side==1 else 'RightEye']:
  center=rig.data.bones[eye_name].head_local
  for upper in [True,False]:
   for n in range(46):
    t=(n+.5)/46;dx=(t*2-1)*.0135;dz=(.0058 if upper else -.0042)*math.sin(t*math.pi)
    y=-math.sqrt(max(.000001,.0146**2-dx*dx-dz*dz))
    base=center+Vector((dx,y,dz))
    length=rng.uniform(.0025,.0045) if upper else rng.uniform(.0012,.0022)
    filament([base+Vector((dx*.08*u,-length*u,(1 if upper else -1)*length*.45*u*u)) for u in [0,.33,.66,1]],.000048)
mesh=bpy.data.meshes.new('Fine brows and eyelash filaments');mesh.from_pydata(vertices,[],faces);mesh.update()
obj=bpy.data.objects.new('Fine_Brows_And_Lashes',mesh);bpy.context.scene.collection.objects.link(obj);obj.parent=rig
material=bpy.data.materials.new('Fine warm brown facial hair');material.use_nodes=True
shader=material.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.022,.008,.004,1);shader.inputs['Roughness'].default_value=.58
mesh.materials.append(material)
for polygon in mesh.polygons: polygon.use_smooth=True
group=obj.vertex_groups.new(name='Head');group.add(list(range(len(vertices))),1,'REPLACE')
modifier=obj.modifiers.new('Facial skinning','ARMATURE');modifier.object=rig
points=KDTree(len(head.data.vertices))
for v in head.data.vertices: points.insert(v.co,v.index)
points.balance();mapping=[points.find(v.co)[1] for v in mesh.vertices]
obj.shape_key_add(name='Basis')
basis=head.data.shape_keys.key_blocks[0]
for original in list(head.data.shape_keys.key_blocks)[1:]:
 key=obj.shape_key_add(name=original.name)
 for v,index in zip(key.data,mapping): v.co+=original.data[index].co-basis.data[index].co
for mat in bpy.data.materials:
 if mat.name=='VitHair':
  for node in mat.node_tree.nodes:
   if node.type=='NORMAL_MAP': node.inputs['Strength'].default_value=.15
# The complete source is preserved; only this corrected copy becomes a candidate.
parts=[o for o in bpy.data.objects if o.type=='MESH' and o.parent==rig and not o.hide_render]
for item in bpy.context.selected_objects:item.select_set(False)
rig.select_set(True)
for item in parts:item.hide_set(False);item.select_set(True)
bpy.context.view_layer.objects.active=rig
rig['surface_revision']='free-surface-v14 — CC0 character with optical eyes and facial hair'
bpy.ops.export_scene.gltf(filepath=str(candidate),export_format='GLB',use_selection=True,export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
if candidate.stat().st_size>80*1024*1024: raise ValueError('Refined candidate exceeds browser limit')
scene=bpy.context.scene;scene.cycles.samples=96;scene.cycles.use_denoising=True
scene.render.resolution_x=760;scene.render.resolution_y=960
scene.render.filepath=str(root/'verification/free-surface-v14-portrait.png')
bpy.ops.wm.save_as_mainfile(filepath=str(source))
bpy.ops.render.render(write_still=True)
scene.camera.data.type='ORTHO';scene.camera.data.ortho_scale=1.95
scene.camera.location=(.25,-3,.95);scene.camera.rotation_euler=(Vector((0,0,.87))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=640;scene.render.resolution_y=900;scene.cycles.samples=48
scene.render.filepath=str(root/'verification/free-surface-v14-full-body.png')
bpy.ops.render.render(write_still=True)
report={'revision':'free-surface-v14','bytes':candidate.stat().st_size,'removed_overlapping_neck_faces':removed,
        'facial_hair_filaments':len(vertices)//8,'cost':0,'photographic_realism_verified':False,
        'extreme_poses_verified':False,'spring_hair_simulation_ported':False,'actual_browser_acceptance':False}
(out/'free-surface-v14-report.json').write_text(json.dumps(report,indent=2))
print('FREE_SURFACE_REFINED',json.dumps(report),flush=True)
