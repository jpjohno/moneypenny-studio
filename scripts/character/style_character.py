"""Derive a clothed styling revision, preserving v9 and its rig/mouth contract."""
import json, math, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
out=root/'.runtime/character-workshop'
dest=out/'Moneypenny-Style-v25.blend'; glb=out/'Moneypenny-Style-v25.glb'
if dest.exists() or glb.exists(): raise SystemExit('Existing v25 preserved')
bpy.ops.wm.open_mainfile(filepath=str(out/'Moneypenny-Surface-Look-v9.blend'))
rig=bpy.data.objects['Adult_Body_Rig']; body=bpy.data.objects['Adult_Anatomy_Surface']; garment=bpy.data.objects['Office_Blouse_And_Skirt']
parts=[o for o in bpy.data.objects if o.parent==rig and o.type=='MESH' and not o.hide_render]

def width(p):
 q=p.copy(); q.x*=1-.06*max(0,min(1,(1.4-p.z)/.06)); return q

def reshape(p):
 q=width(p)
 # A continuous broad bust deformation is shared by body and garment.
 # Keep the back and arms out of the field, with a smooth taper at its edge.
 center=Vector((.10 if p.x>=0 else -.10,-.15,1.16)); d=p-center
 w=math.exp(-((d.x/.105)**4+(d.z/.095)**4)*1.35)
 front=max(0,min(1,(-p.y-.035)/.07))
 q.y-=.16*w*front
 q.x+=(p.x-center.x)*.42*w*front
 q.z+=(p.z-center.z)*.30*w*front
 # Subtle jaw taper and slightly fuller lips; all expression deltas retained.
 if p.y<-.05 and p.z>1.4:
  jaw=math.exp(-((p.z-1.419)/.025)**2)*max(0,min(1,(abs(p.x)-.025)/.035))
  q.x*=1+.018*jaw
  q.x*=1-.035*math.exp(-((p.z-1.402)/.012)**2)
  cheek=max(0,min(1,(abs(p.x)-.022)/.025))
  q.x*=1-.065*cheek*math.exp(-((p.z-1.451)/.018)**2)
  q.x*=1+.035*cheek*math.exp(-((p.z-1.477)/.012)**2)
  lip=math.exp(-((p.x/.028)**4+((p.z-1.431)/.008)**4))
  q.y-=.002*lip; q.z+=(p.z-1.431)*.20*lip
 return q

for obj in parts:
 # Common deformations maintain the existing clothing/body alignment.
 basis=obj.data.shape_keys.key_blocks[0] if obj.data.shape_keys else None
 coordinates=[v.co.copy() for v in (basis.data if basis else obj.data.vertices)]
 for i,p in enumerate(coordinates):
  delta=reshape(p)-p
  if obj.data.shape_keys:
   for key in obj.data.shape_keys.key_blocks:key.data[i].co+=delta
  else:obj.data.vertices[i].co+=delta
 obj.data.update()
# Rebind the enlarged front of the torso to the chest, not the upper arms.
# This keeps the fitted blouse from being pulled sideways during a wave.
rebound=0
for obj in [body,garment]:
 chest_groups={name:(obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)) for name in ['Spine1','Spine2']}
 for v in obj.data.vertices:
  p=v.co
  if 1.03<p.z<1.265 and abs(p.x)<.205 and p.y<-.065:
   for entry in list(v.groups):obj.vertex_groups[entry.group].remove([v.index])
   upper=max(.05,min(.95,(p.z-1.08)/.16))
   chest_groups['Spine1'].add([v.index],1-upper,'REPLACE');chest_groups['Spine2'].add([v.index],upper,'REPLACE');rebound+=1

# Transform the bind skeleton by the same width map, not the bust surface map.
for o in bpy.context.selected_objects:o.select_set(False)
rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for bone in rig.data.edit_bones:
 bone.head=width(bone.head);bone.tail=width(bone.tail)
bpy.ops.object.mode_set(mode='OBJECT')
# Restore a real rest surface for garment clearance measurement (not a posed BVH).
tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],[list(p.vertices) for p in body.data.polygons])
fit=0
for v in garment.data.vertices:
 p,n,_,distance=tree.find_nearest(v.co)
 if p is not None and distance<.045 and (v.co-p).dot(n)<.005:
  v.co=p+n*.005;fit+=1
# Replace the visually stretched stripe print with simple matte tailoring.
# A small tangent normal weave travels through glTF as an actual image.
rng=np.random.default_rng(17); size=512
y,x=np.mgrid[:size,:size]
n=np.empty((size,size,4),dtype=np.float32)
n[:,:,0]=.5+.025*np.sin(x*np.pi/2);n[:,:,1]=.5+.025*np.sin(y*np.pi/2);n[:,:,2]=1;n[:,:,3]=1
weave=bpy.data.images.new('v25 subtle fabric weave',width=size,height=size,alpha=True)
weave.colorspace_settings.name='Non-Color';weave.pixels.foreach_set(n.ravel());weave.pack()
materials=[]
for name,color in [('Champagne matte blouse',(.62,.55,.45,1)),('Ink tailored skirt',(.018,.027,.041,1))]:
 m=bpy.data.materials.new(name);m.use_nodes=True
 s=m.node_tree.nodes.get('Principled BSDF');s.inputs['Base Color'].default_value=color;s.inputs['Roughness'].default_value=.76;s.inputs['Specular IOR Level'].default_value=.24
 tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=weave
 normal=m.node_tree.nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.22
 m.node_tree.links.new(tex.outputs['Color'],normal.inputs['Color']);m.node_tree.links.new(normal.outputs['Normal'],s.inputs['Normal']);materials.append(m)
garment.data.materials.clear()
for m in materials:garment.data.materials.append(m)
for p in garment.data.polygons:p.material_index=0 if p.center.z>1.015 else 1
# Multi-tone dark blonde groom. Retain authored strand variation and brow colour.
colors=[(.16,.082,.026,1),(.29,.17,.065,1),(.075,.033,.011,1),(.40,.26,.115,1),(.22,.12,.04,1)]
for obj in parts:
 for i,m in enumerate(obj.data.materials):
  if not m or not m.use_nodes:continue
  s=next((node for node in m.node_tree.nodes if node.type=='BSDF_PRINCIPLED'),None)
  if not s:continue
  if obj.name in ['Hair_Full_Scalp_Strands','Hair_Individual_Strands'] or 'ponytail01' in obj.name:
   for link in list(s.inputs['Base Color'].links):m.node_tree.links.remove(link)
   s.inputs['Base Color'].default_value=colors[i%5] if 'Strands' in obj.name else (.13,.065,.023,1)
   s.inputs['Roughness'].default_value=.52;s.inputs['Specular IOR Level'].default_value=.23
  if obj.name.endswith('.high-poly'):
   for node in m.node_tree.nodes:
    if node.type!='TEX_IMAGE' or not node.image or 'eye' not in node.image.name:continue
    image=bpy.data.images.load(str(root/'.runtime/character-tools/assets/makehuman_system_assets/eyes/materials/blue_eye.png'),check_existing=False)
    image.name='v25 natural blue eye atlas';image.pack();node.image=image

# Remove the solid brow cards; retain the expression-linked individual hairs.
for obj in list(parts):
 if 'eyebrow001' in obj.name:
  obj.hide_render=True;obj.hide_set(True);parts.remove(obj)
 if obj.name=='Brow_Individual_Strands':
  for m in obj.data.materials:
   shader=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
   shader.inputs['Base Color'].default_value=(.16,.105,.055,1)
   shader.inputs['Roughness'].default_value=.68

# Reuse only the CC0 loose bob from the pinned free character study.
# The source face/body are not substituted. Attach hair to this rig's Head.
hair_source=out/'Moneypenny-Free-Surface-v16.blend'
if not hair_source.exists(): raise FileNotFoundError('Build the pinned free-surface v16 hair source first')
with bpy.data.libraries.load(str(hair_source),link=False) as (available,loaded):
 loaded.objects=['VitHair']
hair=loaded.objects[0];bpy.context.scene.collection.objects.link(hair)
world=hair.matrix_world.copy()
for v in hair.data.vertices:
 p=world@v.co
 v.co=Vector((p.x*.98,(p.y-.049926)*.95-.004509,(p.z-1.534074)*.95+1.408315))
 if v.co.z<1.51:
  fall=max(0,min(1,(1.51-v.co.z)/.15));v.co.z-=.105*fall;v.co.x+=.010*math.sin(p.z*90)*(1 if p.x>0 else -1)*fall
hair.parent=rig;hair.matrix_world=rig.matrix_world.copy();hair.name='Loose_Blonde_Bob'
for modifier in list(hair.modifiers):hair.modifiers.remove(modifier)
hair.vertex_groups.clear();group=hair.vertex_groups.new(name='Head');group.add(list(range(len(hair.data.vertices))),1,'REPLACE')
modifier=hair.modifiers.new('Head skinning','ARMATURE');modifier.object=rig
for m in hair.data.materials:
 for node in m.node_tree.nodes:
  if node.type=='TEX_IMAGE' and node.image and 'diff' in node.image.name.lower():
   image=node.image.copy();image.name='v25 golden blonde bob colour'
   image.pixels[0];a=np.array(image.pixels[:],dtype=np.float32).reshape(-1,4)
   lum=a[:,:3].mean(axis=1);tone=np.clip(lum/max(.001,float(np.quantile(lum,.95))),0,1)**.55
   a[:,0]=.24+tone*.32;a[:,1]=.18+tone*.30;a[:,2]=.095+tone*.24
   image.pixels.foreach_set(a.ravel());image.pack();node.image=image
 s=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 s.inputs['Roughness'].default_value=.55;s.inputs['Specular IOR Level'].default_value=.25
 # Binary cutout avoids self-sorting translucent card layers in the browser.
 if s.inputs['Alpha'].links:
  opacity=s.inputs['Alpha'].links[0].from_socket
  threshold=m.node_tree.nodes.new('ShaderNodeMath');threshold.operation='GREATER_THAN';threshold.inputs[1].default_value=.32
  m.node_tree.links.new(opacity,threshold.inputs[0]);m.node_tree.links.new(threshold.outputs[0],s.inputs['Alpha'])

for old in list(parts):
 if old.name in ['Hair_Full_Scalp_Strands','Hair_Individual_Strands'] or 'ponytail01' in old.name:
  old.hide_render=True;old.hide_set(True);parts.remove(old)
parts.append(hair)
cap_source=next(o for o in bpy.data.objects if o.parent==rig and 'ponytail01' in o.name)
cap=cap_source.copy();cap.data=cap_source.data.copy();cap.name='Blonde_Root_Coverage';bpy.context.scene.collection.objects.link(cap)
cap.hide_render=False;cap.hide_set(False)
import bmesh
bm=bmesh.new();bm.from_mesh(cap.data)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.z<1.49],context='VERTS');bm.to_mesh(cap.data);bm.free();cap.data.update()
root_material=bpy.data.materials.new('Soft blonde root underlayer');root_material.use_nodes=True
shader=root_material.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.20,.14,.075,1);shader.inputs['Roughness'].default_value=.74
cap.data.materials.clear();cap.data.materials.append(root_material);parts.append(cap)

# Local rig and clothing remain available for further refinement.
rig['surface_revision']='v25 — fuller bust, narrower frame, relaxed authored pose, loose blonde bob, blue eyes and matte tailoring'
for obj in bpy.context.selected_objects:obj.select_set(False)
rig.select_set(True)
for obj in parts:
 obj.hide_set(False);obj.select_set(True)
 for modifier in obj.modifiers:
  if modifier.type in ('SUBSURF','SOLIDIFY'):modifier.show_viewport=False;modifier.show_render=False
bpy.context.view_layer.objects.active=rig
# Save the complete authoring body first; only the clothed browser export gets
# an under-garment coverage mask. This is normal game-character clipping control.
bpy.ops.wm.save_as_mainfile(filepath=str(dest))
for obj in bpy.context.selected_objects:obj.select_set(False)
body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
masked=0
for face in body.data.polygons:
 p=face.center
 if .99<p.z<1.285 and abs(p.x)<.20:
  face.select=True;masked+=1
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.delete(type='ONLY_FACE');bpy.ops.object.mode_set(mode='OBJECT')
rig.select_set(True)
for obj in parts:obj.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
if glb.stat().st_size>80*1024*1024:raise ValueError('Browser asset exceeds size budget')
report={'revision':'v25','bytes':glb.stat().st_size,'bust_projection_max_m':.16,'frame_width_scale':.94,'garment_clearance_corrections':fit,'photographic_realism_verified':False,'source_v9_preserved':True,'export_covered_faces':masked,'chest_weight_corrections':rebound}
(out/'style-v25-report.json').write_text(json.dumps(report,indent=2))
print('STYLE_COMPLETE',json.dumps(report),flush=True)
