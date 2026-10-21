"""Replace sparse rear-only strands with a cap-following groom; preserve sources."""
import json
import math
import random
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
out=root/'.runtime/character-workshop'
destination=out/'Moneypenny-Surface-Look-v8.blend'
candidate=out/'Moneypenny-Performance-Candidate-v8.glb'
if destination.exists() or candidate.exists(): raise SystemExit('Existing v8 preserved')
bpy.ops.wm.open_mainfile(filepath=str(out/'Moneypenny-Surface-Look-v7.blend'))
scene=bpy.context.scene
rig=bpy.data.objects['Adult_Body_Rig']
body=bpy.data.objects['Adult_Anatomy_Surface']
cap=next(o for o in bpy.data.objects if o.parent==rig and '.ponytail01' in o.name)
cap.hide_render=False
bpy.data.objects['Hair_Individual_Strands'].hide_render=True
# Retain texture direction, but stop the painted cap producing a white helmet.
for mat in cap.data.materials:
 shader=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 color=shader.inputs['Base Color']
 if color.is_linked:
  original=color.links[0].from_socket
  mix=mat.node_tree.nodes.new('ShaderNodeMixRGB')
  mix.blend_type='MULTIPLY'
  mix.inputs[0].default_value=1
  mix.inputs[2].default_value=(.28,.20,.16,1)
  mat.node_tree.links.new(original,mix.inputs[1])
  mat.node_tree.links.new(mix.outputs[0],color)
 shader.inputs['Roughness'].default_value=.58
 shader.inputs['Specular IOR Level'].default_value=.18
triangles=[]
for polygon in cap.data.polygons:
 ids=list(polygon.vertices)
 for i in range(1,len(ids)-1):
  a,b,c=[cap.matrix_world@cap.data.vertices[k].co for k in (ids[0],ids[i],ids[i+1])]
  center=(a+b+c)/3
  if center.z<1.48 or center.y>.085: continue
  area=(b-a).cross(c-a).length/2
  if area: triangles.append((a,b,c,area))
if not triangles: raise ValueError('No cap surface available for follicles')
rng=random.Random(2026101808)
verts,faces,shades=[],[],[]
center=Vector((0,-.005,1.48))
radii=Vector((.080,.099,.127))
end=Vector((0,.85,.53)).normalized()
for n in range(12000):
 a,b,c,_=rng.choices(triangles,weights=[t[3] for t in triangles])[0]
 u,v=rng.random(),rng.random()
 if u+v>1: u,v=1-u,1-v
 root_point=a*(1-u-v)+b*u+c*v
 direction=Vector([(root_point[i]-center[i])/radii[i] for i in range(3)]).normalized()
 points=[]
 lift=rng.uniform(.0004,.0015)
 for k in range(12):
  t=k/11
  route=direction.lerp(end,t).normalized()
  surface=center+Vector([route[i]*radii[i] for i in range(3)])+route*(.0015+lift)
  point=surface.lerp(root_point,(1-t)**6)
  point.x+=math.sin(t*math.pi)*math.sin(n*.7)*.0005
  points.append(point)
 # Swept lengths terminate at the tied back hair, not on the face.
 last=points[-1]
 length=rng.uniform(.12,.19)
 for k in range(1,5):
  t=k/4
  points.append(last+Vector((math.sin(t*5+n)*.002*t,.012*t,-length*t)))
 start=len(verts)
 shade=rng.randrange(5)
 width=rng.uniform(.00004,.000075)
 for k,p in enumerate(points):
  tangent=(points[min(k+1,len(points)-1)]-points[max(k-1,0)]).normalized()
  radial=(p-center).normalized()
  side=tangent.cross(radial).normalized()
  if side.length<.5: side=Vector((1,0,0))
  radius=width*(1-.94*k/(len(points)-1))
  verts.extend((p-side*radius,p+side*radius))
  if k:
   faces.append((start+(k-1)*2,start+(k-1)*2+1,start+k*2+1,start+k*2))
   shades.append(shade)
mesh=bpy.data.meshes.new('Full scalp swept strand ribbons')
mesh.from_pydata(verts,[],faces)
mesh.update()
groom=bpy.data.objects.new('Hair_Full_Scalp_Strands',mesh)
scene.collection.objects.link(groom)
groom.parent=rig
group=groom.vertex_groups.new(name='Head')
group.add(list(range(len(verts))),1,'REPLACE')
modifier=groom.modifiers.new('Head skinning','ARMATURE')
modifier.object=rig
for index,color in enumerate([(.027,.009,.004,1),(.048,.017,.007,1),(.018,.005,.002,1),(.07,.027,.012,1),(.037,.012,.005,1)]):
 material=bpy.data.materials.new('Full scalp strand tone '+str(index))
 material.use_nodes=True
 material.use_backface_culling=False
 shader=material.node_tree.nodes.get('Principled BSDF')
 shader.inputs['Base Color'].default_value=color
 shader.inputs['Roughness'].default_value=.44
 shader.inputs['Specular IOR Level'].default_value=.25
 mesh.materials.append(material)
for polygon,shade in zip(mesh.polygons,shades):
 polygon.material_index=shade
 polygon.use_smooth=True
groom['asset_source']='Original procedural cap-following strand ribbons, including front hair coverage; not a scan'
groom['strand_count']=12000
# New brow filaments must follow the same expression shapes as their source.
brows=bpy.data.objects['Brow_Individual_Strands']
source=next(o for o in bpy.data.objects if o.parent==rig and 'eyebrow001' in o.name)
if source.data.shape_keys:
 tree=KDTree(len(source.data.vertices))
 for v in source.data.vertices: tree.insert(source.matrix_world@v.co,v.index)
 tree.balance()
 nearest=[tree.find(v.co)[1] for v in brows.data.vertices]
 brows.shape_key_add(name='Basis')
 basis=source.data.shape_keys.key_blocks[0]
 for original in list(source.data.shape_keys.key_blocks)[1:]:
  key=brows.shape_key_add(name=original.name)
  for v,index in zip(key.data,nearest):
   v.co+=source.matrix_world.to_3x3()@(original.data[index].co-basis.data[index].co)
# Reduce duplicate glossy iris response; the separate cornea supplies highlights.
eyes=next(o for o in bpy.data.objects if o.parent==rig and o.name.endswith('.high-poly'))
shader=next(n for n in eyes.data.materials[0].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
shader.inputs['Coat Weight'].default_value=0
shader.inputs['Specular IOR Level'].default_value=.18
shader.inputs['Roughness'].default_value=.35
# More restrained neutral look, selected after the first full-size reviews.
skin=body.data.materials[0]
shader=skin.node_tree.nodes.get('Principled BSDF')
shader.inputs['Subsurface Weight'].default_value=.095
scene.view_settings.exposure=-.5
bpy.data.objects['Large portrait key'].data.energy=40
bpy.data.objects['Cool portrait fill'].data.energy=14.4
bpy.data.objects['Hair separation'].data.energy=12
parts=[o for o in bpy.data.objects if o.parent==rig and o.type=='MESH' and not o.hide_render]
for obj in bpy.context.selected_objects: obj.select_set(False)
rig.hide_set(False)
rig.select_set(True)
for obj in parts:
 obj.hide_set(False)
 obj.select_set(True)
 for mod in obj.modifiers:
  if mod.type in ('SUBSURF','SOLIDIFY'): mod.show_viewport=False; mod.show_render=False
bpy.context.view_layer.objects.active=rig
rig['surface_revision']='v8 — full-scalp strand groom, eye response and expression-linked brows'
bpy.ops.export_scene.gltf(filepath=str(candidate),export_format='GLB',use_selection=True,export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
if candidate.stat().st_size>80*1024*1024: raise ValueError('Candidate exceeds browser limit')
for obj in parts:
 for mod in obj.modifiers:
  if mod.type=='SUBSURF': mod.show_render=True
scene.cycles.samples=64
scene.cycles.use_denoising=True
scene.render.resolution_x=900
scene.render.resolution_y=1125
scene.camera.data.dof.use_dof=False
scene.render.filepath=str(root/'verification/surface-v8-portrait.png')
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
bpy.ops.render.render(write_still=True)
report={'revision':'v8','strands':12000,'groom_vertices':len(verts),'brow_expression_shapes':len(brows.data.shape_keys.key_blocks)-1 if brows.data.shape_keys else 0,
        'bytes':candidate.stat().st_size,'photographic_realism_verified':False,'live_browser_acceptance':False,
        'source':'Moneypenny-Surface-Look-v7.blend','previous_sources_preserved':True}
(out/'surface-v8-report.json').write_text(json.dumps(report,indent=2))
print('GROOM_REBUILD_COMPLETE',json.dumps(report),flush=True)
